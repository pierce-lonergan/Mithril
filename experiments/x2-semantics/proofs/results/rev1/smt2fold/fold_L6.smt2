; benchmark generated from python API
(set-info :status unknown)
(declare-fun v () (_ BitVec 32))
(assert
 (let (($x7571 (= ((_ extract 31 31) (bvand v (_ bv2147483647 32))) (_ bv0 1))))
(not $x7571)))
(check-sat)
