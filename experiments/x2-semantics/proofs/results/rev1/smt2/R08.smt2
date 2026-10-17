; benchmark generated from python API
(set-info :status unknown)
(declare-fun a () (_ BitVec 32))
(declare-fun c () Bool)
(assert
 (let ((?x2769 (ite c a (_ bv0 32))))
(let (($x2770 (= (bvand a (ite c (_ bv4294967295 32) (_ bv0 32))) ?x2769)))
(not $x2770))))
(check-sat)
