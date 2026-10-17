; benchmark generated from python API
(set-info :status unknown)
(declare-fun a () (_ BitVec 32))
(declare-fun b () (_ BitVec 32))
(declare-fun k () Bool)
(assert
 (let ((?x2739 (ite k b a)))
(let (($x2740 (= ?x2739 ?x2739)))
(not $x2740))))
(check-sat)
