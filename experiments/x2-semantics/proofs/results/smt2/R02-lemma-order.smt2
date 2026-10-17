; benchmark generated from python API
(set-info :status unknown)
(declare-fun b () (_ BitVec 32))
(declare-fun a () (_ BitVec 32))
(assert
 (let (($x2871 (= ((_ extract 31 31) b) (_ bv0 1))))
(let (($x2873 (and $x2871 (not (and (= ((_ extract 30 23) b) (_ bv255 8)) (and (distinct ((_ extract 22 0) b) (_ bv0 23)) true))))))
(let (($x2867 (= ((_ extract 31 31) a) (_ bv0 1))))
(let (($x2869 (and $x2867 (not (and (= ((_ extract 30 23) a) (_ bv255 8)) (and (distinct ((_ extract 22 0) a) (_ bv0 23)) true))))))
(let (($x2874 (and $x2869 $x2873)))
(let (($x2886 (=> $x2874 (= (fp.gt ((_ to_fp 8 24) a) ((_ to_fp 8 24) b)) (bvugt a b)))))
(not $x2886))))))))
(check-sat)
