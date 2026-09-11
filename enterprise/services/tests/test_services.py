"""Boundary, accounting, capacity and reproducibility tests for service planning."""
import copy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from enterprise.services import model as m


class ServiceModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=m.load()
        cls.result=m.compare(cls.source,'owned_colo')

    def setUp(self): self.data=copy.deepcopy(self.source)

    def test_scope(self):
        counts=m.validate(self.data)
        self.assertEqual(counts['services'],len(self.data['services']['services']))
        self.assertEqual(counts['workload_classes'],6)
        self.assertTrue({'CP-SWITCH','CP-IDACORE'} <= set(m.unique(self.data['counterparties']['counterparties'])))

    def test_duplicate_service_rejected(self):
        self.data['services']['services'].append(self.data['services']['services'][0])
        with self.assertRaises(ValueError):m.validate(self.data)

    def test_orphan_component_rejected(self):
        self.data['services']['services'][0]['components']=['TEAM-nonexistent']
        with self.assertRaises(ValueError):m.validate(self.data)

    def test_unknown_owner_rejected(self):
        self.data['services']['services'][0]['accountable_owner']='TEAM-missing'
        with self.assertRaises(ValueError):m.validate(self.data)

    def test_internal_audit_cannot_own_operations(self):
        self.data['services']['services'][0]['accountable_owner']='TEAM-audit'
        with self.assertRaises(ValueError):m.validate(self.data)

    def test_unknown_provider_rejected(self):
        self.data['counterparties']['dependencies'][0]['provider_id']='CP-INVENTED'
        with self.assertRaises(ValueError):m.validate(self.data)

    def test_historical_transition_not_current_provider(self):
        self.data['counterparties']['dependencies'][0]['provider_id']='CP-NORTHSTAR'
        with self.assertRaises(ValueError):m.validate(self.data)

    def test_missing_dependency_reverse_link(self):
        self.data['counterparties']['dependencies'][0]['service_ids']=[]
        with self.assertRaises(ValueError):m.validate(self.data)

    def test_incomplete_allocation_rejected(self):
        self.data['components']['components'][0]['allocations']['PROD']='.1'
        with self.assertRaises(ValueError):m.validate(self.data)

    def test_missing_workload_rejected(self):
        self.data['workloads']['workloads'].pop()
        with self.assertRaises(ValueError):m.validate(self.data)

    def test_recovery_not_promoted(self):
        self.data['workloads']['workloads'][0]['approved_rto_hours']='4'
        with self.assertRaises(ValueError):m.validate(self.data)

    def test_no_deployment_claim(self):
        self.data['services']['services'][0]['delivery_state']='OPERATIONAL'
        with self.assertRaises(ValueError):m.validate(self.data)

    def test_invalid_price(self):
        self.data['economics']['prices']['cpu_node']='-1'
        with self.assertRaises(ValueError):m.validate(self.data)

    def test_nan_rejected(self):
        self.data['economics']['prices']['cpu_node']='NaN'
        with self.assertRaises(ValueError):m.validate(self.data)

    def test_boolean_not_number(self):
        with self.assertRaises(ValueError):m.decimal(True)

    def test_invalid_headroom(self):
        self.data['economics']['capacity']['normal_utilization_ceiling']='1'
        with self.assertRaises(ValueError):m.validate(self.data)

    def test_invalid_recovery_fraction(self):
        self.data['workloads']['recovery_fractions']['PROD']='2'
        with self.assertRaises(ValueError):m.validate(self.data)

    def test_vendor_credit_cannot_exceed_allowance(self):
        self.data['economics']['bridge']['vendor_overlap_approved_usd']=216001
        with self.assertRaises(ValueError):m.financial_bridge(self.data)

    def test_negative_credit_rejected(self):
        self.data['economics']['bridge']['vendor_overlap_approved_usd']=-1
        with self.assertRaises(ValueError):m.financial_bridge(self.data)

    def test_no_arbitrary_forecast_offset(self):
        b=m.financial_bridge(self.data)
        self.assertEqual(b['baseline']['generic_vendor_annual_usd'],216000)
        self.assertEqual(b['baseline']['corporate_facilities_annual_usd'],1140000)
        self.assertEqual(b['baseline']['ess_annual_payroll_usd'],6720000)
        self.assertIsNone(b['approved_successor_net_incremental_usd'])
        self.assertTrue(all(v is None for v in b['approved_offsets'].values()))

    def test_education_and_recruiting_existing_owners(self):
        s=m.unique(self.data['services']['services'])
        self.assertEqual(s['SVC-education']['accountable_owner'],'TEAM-education')
        self.assertEqual(s['SVC-recruiting']['accountable_owner'],'TEAM-people')
        self.assertEqual(s['SVC-education']['sourcing'],'INTERNAL')

    def test_no_invented_supplier_selection(self):
        deps=self.data['counterparties']['dependencies']
        self.assertEqual({d['id']: d['provider_id'] for d in deps if d['provider_id'] is not None}, {
            'DEP-kgm-host':'CP-KGM', 'DEP-demotte-host':'CP-DEMOTTE', 'DEP-class-i':'CP-UP',
            'DEP-colo-primary':'CP-SWITCH', 'DEP-colo-recovery':'CP-IDACORE'})
        self.assertTrue(all(d['agreement_id'] is None for d in deps))

    def test_restricted_owned_in_every_alternative(self):
        for mode in self.data['economics']['modes']:
            fp=m.footprint(self.data,mode,0)
            owned={r['domain']:r for r in fp['owned']}
            self.assertIn('RESTRICTED',owned)
            self.assertIn('RECOVERY_RESTRICTED',owned)
            self.assertEqual(owned['RESTRICTED']['gpu_units'],8)

    def test_capacity_covers_one_cpu_node_failure(self):
        for mode in self.data['economics']['modes']:
            for year in range(5):
                for row in m.footprint(self.data,mode,year)['owned']:
                    self.assertGreaterEqual(m.decimal(row['n_minus_1_usable_vcpu']),m.decimal(row['required_vcpu']))
                    self.assertGreaterEqual(m.decimal(row['n_minus_1_usable_memory_gib']),m.decimal(row['required_memory_gib']))
                    self.assertGreaterEqual(m.decimal(row['usable_storage_tib']),m.decimal(row['required_storage_tib']))

    def test_recovery_storage_not_reduced_with_cpu(self):
        fp=m.footprint(self.data,'owned_colo',0)
        self.assertEqual(fp['demands']['RECOVERY_PROD']['usable_storage_tib'],fp['demands']['PROD']['usable_storage_tib'])
        self.assertEqual(fp['demands']['RECOVERY_PROD']['vcpu'],fp['demands']['PROD']['vcpu']*m.D('.40'))

    def test_recovery_not_double_counted_in_backup(self):
        fp=m.footprint(self.data,'owned_colo',0)
        self.assertEqual(fp['backup_tib'],m.D(50+100+20+20+5)*2)

    def test_no_owned_plant_in_colo_alternative(self):
        self.assertNotIn('primary:plant',m.footprint(self.data,'owned_colo',0)['assets'])
        fp=m.footprint(self.data,'owned_facility',0)
        self.assertIn('primary:plant',fp['assets'])
        self.assertNotIn('recovery:plant',fp['assets'])

    def test_plant_scales_above_nameplate(self):
        fp=m.footprint(self.data,'owned_facility',4,m.D('10'))
        capacity=m.decimal(self.data['economics']['capacity']['owned_plant_it_kw_capacity'])
        self.assertGreaterEqual(fp['assets']['primary:plant']['quantity']*capacity,fp['locations']['primary']['kw'])

    def test_depreciation_begins_next_month(self):
        rows=self.result['monthly']
        self.assertEqual(rows[0]['depreciation_usd'],'0.00')
        self.assertGreater(m.decimal(rows[1]['depreciation_usd']),0)

    def test_hardware_refresh_month49(self):
        initial={r['key'] for r in self.result['asset_cohorts'] if r['month']==1}
        refreshed={r['key'] for r in self.result['asset_cohorts'] if r['month']==49}
        self.assertTrue(initial <= refreshed)

    def test_capex_not_double_counted(self):
        for r in self.result['monthly']:
            self.assertLessEqual(abs(m.decimal(r['cash_total_usd'])-m.decimal(r['capex_usd'])-m.decimal(r['cash_opex_usd'])),m.D('.01'))
            self.assertLessEqual(abs(m.decimal(r['pnl_cost_usd'])-m.decimal(r['depreciation_usd'])-m.decimal(r['cash_opex_usd'])),m.D('.01'))

    def test_asset_roll_forward(self):
        s=self.result['summary']
        self.assertLessEqual(abs(m.decimal(s['capex_60_month_usd'])-m.decimal(s['depreciation_60_month_usd'])-m.decimal(s['closing_net_book_usd'])),m.D('.10'))

    def test_shared_staff_cost_allocations_reconcile(self):
        for row in m.staffing(self.data,'owned_colo'):
            total=sum(m.decimal(v) for v in row['allocated_costs'].values())
            self.assertLessEqual(abs(total-m.decimal(row['annual_gross_loaded_usd'])),m.D('.05'))
            self.assertIsNone(row['incremental_fte'])

    def test_continuous_seat_includes_relief(self):
        rows=m.staffing(self.data,'owned_facility')
        seat=next(r for r in rows if r['component_id']=='OWNED-physical-coverage')
        self.assertEqual(m.decimal(seat['required_fte']),m.D('5.6'))
        self.assertEqual(seat['funded_positions_if_dedicated'],6)

    def test_annual_effort_increases_with_demand(self):
        staff=self.result['staffing']
        self.assertGreater(staff[-1]['required_fte'],staff[0]['required_fte'])

    def test_invalid_sensitivity(self):
        with self.assertRaises(ValueError):m.compare(self.data,'owned_colo',m.ZERO)

    def test_higher_prices_raise_cost(self):
        a=m.compare(self.data,'owned_colo',price_factor=m.D('.7'))['summary']
        b=m.compare(self.data,'owned_colo',price_factor=m.D('1.4'))['summary']
        self.assertLess(m.decimal(a['cash_60_month_usd']),m.decimal(b['cash_60_month_usd']))

    def test_manifest_is_reproducible(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/'a';b=Path(tmp)/'b'
            m.build(self.data,a,sensitivity=False)
            m.build(self.data,b,sensitivity=False)
            self.assertEqual((a/'manifest.json').read_bytes(),(b/'manifest.json').read_bytes())

    def test_database_links_and_no_silent_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'services.sqlite3'
            m.write_database(p,self.data,[self.result['summary']])
            with closing(sqlite3.connect(p)) as con:
                self.assertEqual(con.execute('select count(*) from service').fetchone()[0],57)
                self.assertFalse(con.execute('pragma foreign_key_check').fetchall())
                self.assertGreater(con.execute('select count(*) from service_dependency').fetchone()[0],57)
            with self.assertRaises(ValueError):m.write_database(p,self.data,[])

    def test_transition_has_complete_calendar(self):
        r=m.compare(self.data,'phased_ownership')
        rows=r['monthly']
        self.assertEqual(len(rows),60)
        self.assertEqual(rows[5]['active_mode'],'cloud_transition')
        self.assertEqual(rows[6]['active_mode'],'hybrid_transition')
        self.assertEqual(rows[18]['active_mode'],'owned_colo')
        self.assertGreater(m.decimal(rows[6]['capex_usd']),0)
        self.assertEqual(sum(m.decimal(row['transition_usd'])>0 for row in rows),3)

    def test_transition_overlap_rejected(self):
        self.data['economics']['transition_schedule'][1]['from_month']=6
        with self.assertRaises(ValueError):m.validate(self.data)

    def test_transition_refreshes_midyear_assets(self):
        r=m.compare(self.data,'phased_ownership')
        early={c['key'] for c in r['asset_cohorts'] if c['month']==7}
        late={c['key'] for c in r['asset_cohorts'] if c['month']==55}
        self.assertTrue(early <= late)

    def test_repository_validation_does_not_silently_skip_missing_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'Missing repository source'):
                m.validate(self.data,Path(tmp))


if __name__=='__main__':unittest.main()
