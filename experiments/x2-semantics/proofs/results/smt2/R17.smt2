; benchmark generated from python API
(set-info :status unknown)
(declare-fun q () (_ BitVec 32))
(assert
 (let ((?x6699 ((_ extract 7 0) q)))
(let ((?x6687 (ite (bvsgt q (_ bv32767 32)) (_ bv32767 32) (ite (bvslt q (_ bv4294934528 32)) (_ bv4294934528 32) q))))
(let ((?x6698 ((_ extract 7 0) (ite (bvsgt ?x6687 (_ bv127 32)) (_ bv127 32) (ite (bvslt ?x6687 (_ bv4294967168 32)) (_ bv4294967168 32) ?x6687)))))
(let (($x6701 (=> (and (bvsge q (_ bv4294967169 32)) (bvsle q (_ bv127 32))) (= ?x6698 ?x6699))))
(not $x6701))))))
(check-sat)
