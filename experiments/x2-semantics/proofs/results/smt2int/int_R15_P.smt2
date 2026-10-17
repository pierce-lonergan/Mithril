; benchmark generated from python API
(set-info :status unknown)
(declare-fun x () (_ BitVec 8))
(declare-fun n () (_ BitVec 8))
(assert
 (let ((?x419 ((_ sign_extend 24) x)))
(let ((?x416 ((_ zero_extend 24) n)))
(let ((?x421 (bvmul ?x416 ?x419)))
(let (($x429 (and (= (bvmul (bvsub ?x416 (_ bv8 32)) ?x419) (bvsub ?x421 (bvmul (_ bv8 32) ?x419))) (bvsle ?x421 (_ bv1905 32)) (bvsge ?x421 (_ bv4294965391 32)))))
(let (($x430 (=> (and (bvule n (_ bv15 8)) (and (bvsge x (_ bv129 8)) (bvsle x (_ bv127 8)))) $x429)))
(not $x430)))))))
(check-sat)
