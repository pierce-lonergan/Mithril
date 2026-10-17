; benchmark generated from python API
(set-info :status unknown)
(declare-fun hi16 () (_ BitVec 16))
(declare-fun lo16 () (_ BitVec 16))
(assert
 (let (($x58 (= ((_ sign_extend 16) (bvadd lo16 hi16)) (bvadd ((_ sign_extend 16) lo16) ((_ sign_extend 16) hi16)))))
(let (($x51 (bvsle hi16 (_ bv3810 16))))
(let (($x49 (bvsle lo16 (_ bv3810 16))))
(let (($x59 (=> (and (bvsge lo16 (_ bv61726 16)) $x49 (bvsge hi16 (_ bv61726 16)) $x51) $x58)))
(not $x59))))))
(check-sat)
