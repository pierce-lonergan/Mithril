; benchmark generated from python API
(set-info :status unknown)
(declare-fun v () (_ BitVec 32))
(assert
 (let ((?x2692 ((_ extract 22 0) v)))
(let (($x2693 (and (distinct ?x2692 (_ bv0 23)) true)))
(let ((?x2690 ((_ extract 30 23) v)))
(let (($x2691 (= ?x2690 (_ bv255 8))))
(let (($x2694 (and $x2691 $x2693)))
(let ((?x2725 (ite $x2694 (_ bv0 32) v)))
(let (($x2726 (= (bvand v (ite (not (fp.isNaN ((_ to_fp 8 24) v))) (_ bv4294967295 32) (_ bv0 32))) ?x2725)))
(not $x2726)))))))))
(check-sat)
