; benchmark generated from python API
(set-info :status unknown)
(declare-fun x () (_ BitVec 8))
(declare-fun q () (_ BitVec 8))
(assert
 (let ((?x419 ((_ sign_extend 24) x)))
(let ((?x884 ((_ zero_extend 24) (bvxor q (_ bv128 8)))))
(let ((?x890 (bvmul ?x884 ?x419)))
(let (($x896 (and (= ?x884 (bvadd ((_ sign_extend 24) q) (_ bv128 32))) (= (bvmul ((_ sign_extend 24) q) ?x419) (bvsub ?x890 (bvmul (_ bv128 32) ?x419))) (bvsle ?x890 (_ bv32385 32)) (bvsge ?x890 (_ bv4294934911 32)))))
(let (($x414 (and (bvsge x (_ bv129 8)) (bvsle x (_ bv127 8)))))
(let (($x897 (=> $x414 $x896)))
(not $x897))))))))
(check-sat)
