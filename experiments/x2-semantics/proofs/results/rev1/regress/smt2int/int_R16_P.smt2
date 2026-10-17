; benchmark generated from python API
(set-info :status unknown)
(declare-fun x () (_ BitVec 8))
(declare-fun q () (_ BitVec 8))
(assert
 (let ((?x408 ((_ sign_extend 24) x)))
(let ((?x873 ((_ zero_extend 24) (bvxor q (_ bv128 8)))))
(let ((?x879 (bvmul ?x873 ?x408)))
(let (($x885 (and (= ?x873 (bvadd ((_ sign_extend 24) q) (_ bv128 32))) (= (bvmul ((_ sign_extend 24) q) ?x408) (bvsub ?x879 (bvmul (_ bv128 32) ?x408))) (bvsle ?x879 (_ bv32385 32)) (bvsge ?x879 (_ bv4294934911 32)))))
(let (($x403 (and (bvsge x (_ bv129 8)) (bvsle x (_ bv127 8)))))
(let (($x886 (=> $x403 $x885)))
(not $x886))))))))
(check-sat)
