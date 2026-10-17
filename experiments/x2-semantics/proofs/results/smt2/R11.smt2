; benchmark generated from python API
(set-info :status unknown)
(declare-fun a () (_ BitVec 32))
(declare-fun k () Bool)
(assert
 (let ((?x2743 (ite k a (_ bv0 32))))
(let (($x2744 (= ?x2743 ?x2743)))
(not $x2744))))
(check-sat)
