const assert=require('node:assert/strict');const {rect,project,inside,boxFaces}=require('./viewer.js');const c={target:[0,0,0],yaw:0,pitch:Math.PI/4,width:800,height:600,pan:[0,0],scale:10};assert.deepEqual(rect({x:1,y:2,width:3,depth:4}),[1,2,3,4]);assert.deepEqual(project([0,0,0],c),[400,300,0]);assert.equal(project([1,0,0],c)[0],410);assert.ok(project([0,0,1],c)[1]<300);assert.equal(inside([1,1],[[0,0],[2,0],[2,2],[0,2]]),true);assert.equal(inside([3,1],[[0,0],[2,0],[2,2],[0,2]]),false);const f=boxFaces([0,0,0,2,3,4],c,{id:'b'},'#aabbcc');assert.equal(f.length,5);assert.ok(f.every(x=>x.points.length===4&&Number.isFinite(x.depth)));console.log('PASS local frame, projection, faces and picking');
assert.equal(project([1,0,0],{...c,scale:20})[0],420);
assert.equal(project([0,0,0],{...c,pan:[12,-8]})[0],412);
assert.equal(project([0,0,0],{...c,pan:[12,-8]})[1],292);
assert.ok(Math.abs(project([1,0,0],{...c,yaw:Math.PI/2})[0]-400)<1e-9);
const near=boxFaces([0,0,4,2,3,1],c,{id:'upper'},'#aabbcc');
assert.ok(Math.max(...near.map(f=>f.depth))>Math.max(...f.map(f=>f.depth)));

const {validateComparison}=require('./viewer.js');
const sites=[{id:'s',buildings:[{floors:[{id:'f'}]}]}];
const payload={comparisons:[{site_id:'s',before_revision:'a',after_revision:'b',changes:[],overlays:[{floor_id:'f',before_rooms:[{id:'r',rect_m:[0,0,3,4]}],after_rooms:[]}]}]};
assert.equal(validateComparison(payload,sites).length,1);
for(const mutate of [p=>p.comparisons[0].site_id='bad',p=>p.comparisons[0].overlays[0].floor_id='bad',p=>p.comparisons[0].overlays[0].before_rooms[0].rect_m[2]=-1,p=>p.comparisons[0].overlays[0].before_rooms[0].rect_m[0]=NaN]){const bad=structuredClone(payload);mutate(bad);assert.throws(()=>validateComparison(bad,sites));}
console.log('PASS comparison import shape, identity and geometry validation');
