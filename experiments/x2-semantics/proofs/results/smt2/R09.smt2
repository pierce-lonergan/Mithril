; benchmark generated from python API
(set-info :status unknown)
(declare-fun a () (_ BitVec 32))
(declare-fun b () (_ BitVec 32))
(declare-fun c () Bool)
(assert
 (let ((?x2731 (ite c b a)))
(let (($x2732 (= (ite (= ((_ extract 31 31) (ite c (_ bv4294967295 32) (_ bv0 32))) (_ bv1 1)) b a) ?x2731)))
(not $x2732))))
(check-sat)
