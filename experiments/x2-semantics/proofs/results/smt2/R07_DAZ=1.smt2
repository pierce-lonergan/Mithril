; benchmark generated from python API
(set-info :status unknown)
(declare-fun v () (_ BitVec 32))
(assert
 (let ((?x2692 ((_ extract 22 0) v)))
(let (($x2693 (and (distinct ?x2692 (_ bv0 23)) true)))
(let ((?x2690 ((_ extract 30 23) v)))
(let (($x2691 (= ?x2690 (_ bv255 8))))
(let (($x2694 (and $x2691 $x2693)))
(let (($x2696 (not $x2694)))
(let ((?x2705 ((_ to_fp 8 24) (ite (and true (and (= ?x2690 (_ bv0 8)) $x2693)) (bvand v (_ bv2147483648 32)) v))))
(let (($x2713 (= (or (fp.lt ?x2705 ?x2705) (fp.eq ?x2705 ?x2705) (fp.gt ?x2705 ?x2705)) $x2696)))
(not $x2713))))))))))
(check-sat)
