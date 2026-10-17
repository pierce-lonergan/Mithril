; benchmark generated from python API
(set-info :status unknown)
(declare-fun x () (_ BitVec 8))
(declare-fun n () (_ BitVec 8))
(assert
 (let ((?x408 ((_ sign_extend 24) x)))
(let ((?x405 ((_ zero_extend 24) n)))
(let ((?x410 (bvmul ?x405 ?x408)))
(let (($x418 (and (= (bvmul (bvsub ?x405 (_ bv8 32)) ?x408) (bvsub ?x410 (bvmul (_ bv8 32) ?x408))) (bvsle ?x410 (_ bv1905 32)) (bvsge ?x410 (_ bv4294965391 32)))))
(let (($x419 (=> (and (bvule n (_ bv15 8)) (and (bvsge x (_ bv129 8)) (bvsle x (_ bv127 8)))) $x418)))
(not $x419)))))))
(check-sat)
