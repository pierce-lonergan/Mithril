; benchmark generated from python API
(set-info :status unknown)
(declare-fun q () (_ BitVec 32))
(assert
 (let ((?x6921 ((_ extract 7 0) q)))
(let ((?x6909 (ite (bvsgt q (_ bv32767 32)) (_ bv32767 32) (ite (bvslt q (_ bv4294934528 32)) (_ bv4294934528 32) q))))
(let ((?x6920 ((_ extract 7 0) (ite (bvsgt ?x6909 (_ bv127 32)) (_ bv127 32) (ite (bvslt ?x6909 (_ bv4294967168 32)) (_ bv4294967168 32) ?x6909)))))
(let (($x6923 (=> (and (bvsge q (_ bv4294967169 32)) (bvsle q (_ bv127 32))) (= ?x6920 ?x6921))))
(not $x6923))))))
(check-sat)
