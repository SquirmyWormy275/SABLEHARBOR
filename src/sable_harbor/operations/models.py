from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, ForeignKeyConstraint, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from sable_harbor.accounting.models import Base, GenerationOwnedMixin


class PayrollRun(GenerationOwnedMixin, Base):
    __tablename__ = "payroll_run"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    pay_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(24))
    gross_pay: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    employer_cost: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))


class PayrollLine(GenerationOwnedMixin, Base):
    __tablename__ = "payroll_line"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    payroll_run_id: Mapped[str] = mapped_column(ForeignKey("payroll_run.id"))
    worker_id: Mapped[str] = mapped_column(ForeignKey("worker.id"))
    gross_pay: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    employer_cost: Mapped[Decimal] = mapped_column(Numeric(20, 4))


class Vendor(GenerationOwnedMixin, Base):
    __tablename__ = "vendor"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(60))
    __table_args__ = (
        UniqueConstraint("generation_run_id", "code"),
        UniqueConstraint("id", "generation_run_id", name="uq_vendor_id_generation_run_id"),
    )


class PurchaseOrder(GenerationOwnedMixin, Base):
    __tablename__ = "purchase_order"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendor.id"))
    po_number: Mapped[str] = mapped_column(String(40))
    order_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    status: Mapped[str] = mapped_column(String(24))
    __table_args__ = (
        UniqueConstraint("generation_run_id", "po_number"),
        ForeignKeyConstraint(
            ["vendor_id", "generation_run_id"],
            ["vendor.id", "vendor.generation_run_id"],
            name="fk_purchase_order_vendor_id_same_run",
        ),
    )


class GoodsReceipt(GenerationOwnedMixin, Base):
    __tablename__ = "goods_receipt"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    purchase_order_id: Mapped[str] = mapped_column(ForeignKey("purchase_order.id"))
    receipt_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))


class VendorBill(GenerationOwnedMixin, Base):
    __tablename__ = "vendor_bill"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    purchase_order_id: Mapped[str] = mapped_column(ForeignKey("purchase_order.id"))
    receipt_id: Mapped[str] = mapped_column(ForeignKey("goods_receipt.id"))
    bill_number: Mapped[str] = mapped_column(String(40))
    bill_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    match_status: Mapped[str] = mapped_column(String(24))
    journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))
    __table_args__ = (UniqueConstraint("generation_run_id", "bill_number"),)


class VendorPayment(GenerationOwnedMixin, Base):
    __tablename__ = "vendor_payment"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    vendor_bill_id: Mapped[str] = mapped_column(ForeignKey("vendor_bill.id"))
    payment_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))


class DepreciationRecord(GenerationOwnedMixin, Base):
    __tablename__ = "depreciation_record"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("fixed_asset.id"))
    period_code: Mapped[str] = mapped_column(String(7))
    depreciation_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))


class DebtFacility(GenerationOwnedMixin, Base):
    __tablename__ = "debt_facility"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("legal_entity.id"))
    facility_number: Mapped[str] = mapped_column(String(40))
    commitment: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    annual_rate: Mapped[Decimal] = mapped_column(Numeric(12, 8))
    __table_args__ = (UniqueConstraint("generation_run_id", "facility_number"),)


class DebtDraw(GenerationOwnedMixin, Base):
    __tablename__ = "debt_draw"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    facility_id: Mapped[str] = mapped_column(ForeignKey("debt_facility.id"))
    draw_date: Mapped[date] = mapped_column(Date)
    principal: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))


class DebtRepayment(GenerationOwnedMixin, Base):
    __tablename__ = "debt_repayment"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    debt_draw_id: Mapped[str] = mapped_column(ForeignKey("debt_draw.id"))
    repayment_date: Mapped[date] = mapped_column(Date)
    principal: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))


class InterestAccrual(GenerationOwnedMixin, Base):
    __tablename__ = "interest_accrual"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    debt_draw_id: Mapped[str] = mapped_column(ForeignKey("debt_draw.id"))
    accrual_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entry.id"))
