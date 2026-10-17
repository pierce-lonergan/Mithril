; benchmark generated from python API
(set-info :status unknown)
(declare-fun a () (_ BitVec 32))
(declare-fun c () Bool)
(assert
 (let ((?x2720 (ite c a (_ bv0 32))))
(let (($x2721 (= (bvand a (ite c (_ bv4294967295 32) (_ bv0 32))) ?x2720)))
(not $x2721))))
(check-sat)
