;;; GUID-TOOLS.LSP - Persistent GUID maintenance tools for DWG objects
;;;
;;; Commands:
;;;   RADIKA_GUID_REFRESH
;;;   RADIKA_GUID_AUDIT
;;;   RADIKA_GUID_REPAIR

(vl-load-com)

(defun rg-ensure-regapp (app /)
  (if (null (tblsearch "APPID" app))
    (entmake (list (cons 0 "APPID") (cons 2 app) (cons 70 0))))
  app
)

(defun rg-rand32 ( / seed )
  (if (not (boundp '*rg-seed*))
    (setq *rg-seed* (fix (* 1000000.0 (rem (getvar "DATE") 1.0)))))
  (setq seed (rem (+ (* *rg-seed* 1664525.0) 1013904223.0) 4294967296.0))
  (setq *rg-seed* seed)
  seed
)

(defun rg-hex-char ( n ) (substr "0123456789abcdef" (1+ n) 1))

(defun rg-rand-hex ( n / i out )
  (setq i 0 out "")
  (while (< i n)
    (setq out (strcat out (rg-hex-char (fix (rem (rg-rand32) 16.0)))))
    (setq i (1+ i)))
  out
)

(defun radika-guid-generate ( / obj g y )
  ;; Prefer Windows COM GUID generator for robust uniqueness.
  (setq obj (vl-catch-all-apply 'vlax-create-object (list "Scriptlet.TypeLib")))
  (if (not (vl-catch-all-error-p obj))
    (progn
      (setq g (vlax-get-property obj 'Guid)) ;; "{xxxxxxxx-....}"
      (vlax-release-object obj)
      (strcase (vl-string-trim "{}" g) T))
    ;; Fallback: old pseudo-random v4-like format
    (progn
      (setq y (+ 8 (fix (rem (rg-rand32) 4.0))))
      (strcat
        (rg-rand-hex 8) "-"
        (rg-rand-hex 4) "-4"
        (rg-rand-hex 3) "-"
        (rg-hex-char y)
        (rg-rand-hex 3) "-"
        (rg-rand-hex 12))))
)

(defun radika-guid-valid-p ( s / v )
  (setq v (strcase (vl-string-trim " " (if s s "")) T))
  (and
    (= (strlen v) 36)
    (= (substr v 9 1) "-")
    (= (substr v 14 1) "-")
    (= (substr v 19 1) "-")
    (= (substr v 24 1) "-")
    (wcmatch v "[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]")))

(defun rg-xdata-read-map ( ent / xd out pair txt pos key val )
  (setq out nil)
  (setq xd (assoc -3 (entget ent '("RADIKA_REIKAVARAUS"))))
  (if xd
    (foreach pair (cdr (cadr xd))
      (if (and (= (type pair) 'LIST) (= (car pair) 1000))
        (progn
          (setq txt (cdr pair))
          (setq pos (vl-string-search "=" txt))
          (if pos
            (progn
              (setq key (strcase (substr txt 1 pos)))
              (setq val (substr txt (+ pos 2)))
              (if (and key (/= key "")) (setq out (cons (cons key val) out)))))))))
  (reverse out)
)

(defun rg-xdata-write-map ( ent kv / obj types vals tarr varr )
  (if (and ent (entget ent))
    (progn
      (rg-ensure-regapp "RADIKA_REIKAVARAUS")
      (setq obj (vlax-ename->vla-object ent))
      (setq types (list 1001))
      (setq vals  (list "RADIKA_REIKAVARAUS"))
      (foreach pair kv
        (setq types (append types (list 1000)))
        (setq vals (append vals (list (strcat (car pair) "=" (cdr pair))))))
      (setq tarr (vlax-make-safearray vlax-vbinteger (cons 0 (1- (length types)))))
      (setq varr (vlax-make-safearray vlax-vbvariant (cons 0 (1- (length vals)))))
      (vlax-safearray-fill tarr types)
      (vlax-safearray-fill varr vals)
      (if (vl-catch-all-error-p (vl-catch-all-apply 'vla-SetXData (list obj tarr varr)))
        nil
        (progn (entupd ent) T)))))

(defun radika-guid-get ( ent / m ) (setq m (rg-xdata-read-map ent)) (cdr (assoc "GUID" m)))

(defun radika-guid-set ( ent guid / m out pair )
  (setq m (rg-xdata-read-map ent))
  (setq out (list (cons "GUID" guid)))
  (foreach pair m
    (if (/= (car pair) "GUID")
      (setq out (append out (list pair)))))
  (rg-xdata-write-map ent out)
)

(defun rg-kyl-selection ( / ss )
  ;; all entities on layers that start with KYL (case-insensitive)
  (setq ss (ssget "_X" (list (cons 8 "KYL*"))))
  ss
)

(defun rg-guid-eligible-p (ent / dxf typ lay)
  (setq dxf (entget ent))
  (setq typ (strcase (cdr (assoc 0 dxf))))
  (setq lay (strcase (cdr (assoc 8 dxf))))
  ;; Only process model-object types we actually want GUIDs for.
  ;; This excludes plain 2D annotations/random linework and KYL-KALUSTEET*.
  (and
    (member typ '("INSERT" "3DSOLID" "MESH" "POLYLINE" "LWPOLYLINE"))
    (not (wcmatch lay "*KALUSTE*"))))

(defun rg-ent-handle (ent / dxf)
  (setq dxf (entget ent))
  (if dxf (cdr (assoc 5 dxf)) "<?>"))

(defun rg-ent-layer (ent / dxf)
  (setq dxf (entget ent))
  (if dxf (cdr (assoc 8 dxf)) "<?>"))

(defun rg-ent-type (ent / dxf)
  (setq dxf (entget ent))
  (if dxf (cdr (assoc 0 dxf)) "<?>"))

(defun c:RGUID_REFRESH_AUTO ( / ss i e g added kept skipped )
  (setq ss (rg-kyl-selection))
  (if (null ss)
    (princ "\nEi KYL*-layerin objekteja.")
    (progn
      (setq i 0 added 0 kept 0 skipped 0)
      (while (< i (sslength ss))
        (setq e (ssname ss i))
        (if (rg-guid-eligible-p e)
          (progn
            (setq g (radika-guid-get e))
            (if (and g (/= (vl-string-trim " " g) ""))
              (setq kept (1+ kept))
              (if (radika-guid-set e (radika-guid-generate))
                (setq added (1+ added)))))
          (setq skipped (1+ skipped)))
        (setq i (1+ i)))
      (princ (strcat "\nRADIKA_GUID_REFRESH: lisatty " (itoa added) ", sailytetty " (itoa kept) "."))))
  (princ))

(defun c:RGUID_AUDIT_AUTO ( / ss i e g key item groups missing invalid dupGroups skipped )
  (setq ss (rg-kyl-selection))
  (if (null ss)
    (princ "\nEi KYL*-layerin objekteja.")
    (progn
      (setq i 0 groups nil missing 0 invalid 0 skipped 0)
      (while (< i (sslength ss))
        (setq e (ssname ss i))
        (if (rg-guid-eligible-p e)
          (progn
            (setq g (radika-guid-get e))
            (if (or (null g) (= (vl-string-trim " " g) ""))
              (setq missing (1+ missing))
              (progn
                (if (not (radika-guid-valid-p g))
                  (setq invalid (1+ invalid)))
                (setq key (strcase g T))
                (setq item (assoc key groups))
                (if item
                  (setq groups (subst (cons key (cons e (cdr item))) item groups))
                  (setq groups (cons (cons key (list e)) groups))))))
          (setq skipped (1+ skipped)))
        (setq i (1+ i)))
      (setq dupGroups 0)
      (foreach item groups
        (if (> (length (cdr item)) 1)
          (setq dupGroups (1+ dupGroups))))
      (princ (strcat "\nRADIKA_GUID_AUDIT: puuttuvat=" (itoa missing)
                     ", virheelliset=" (itoa invalid)
                     ", duplikaattiryhmat=" (itoa dupGroups)
                     ", ohitetut=" (itoa skipped) "."))
      (if (> dupGroups 0)
        (foreach item groups
          (if (> (length (cdr item)) 1)
            (progn
              (princ (strcat "\n  DUP " (car item) " -> " (itoa (length (cdr item))) " kpl"))
              (foreach e (cdr item)
                (princ (strcat "\n    - handle=" (rg-ent-handle e)
                               " layer=" (rg-ent-layer e)
                               " type=" (rg-ent-type e))))))))))
  (princ)
)

(defun c:RGUID_REPAIR_AUTO ( / ss i e g key item groups fixedMissing fixedDup idx lst skipped )
  (setq ss (rg-kyl-selection))
  (if (null ss)
    (princ "\nEi KYL*-layerin objekteja.")
    (progn
      (setq i 0 fixedMissing 0 skipped 0)
      (while (< i (sslength ss))
        (setq e (ssname ss i))
        (if (rg-guid-eligible-p e)
          (progn
            (setq g (radika-guid-get e))
            (if (or (null g) (= (vl-string-trim " " g) ""))
              (if (radika-guid-set e (radika-guid-generate))
                (setq fixedMissing (1+ fixedMissing)))))
          (setq skipped (1+ skipped)))
        (setq i (1+ i)))
      (setq i 0 groups nil)
      (while (< i (sslength ss))
        (setq e (ssname ss i))
        (setq g nil)
        (if (rg-guid-eligible-p e)
          (setq g (radika-guid-get e)))
        (if (and g (/= (vl-string-trim " " g) ""))
          (progn
            (setq key (strcase g T))
            (setq item (assoc key groups))
            (if item
              (setq groups (subst (cons key (append (cdr item) (list e))) item groups))
              (setq groups (cons (cons key (list e)) groups)))))
        (setq i (1+ i)))
      (setq fixedDup 0)
      (foreach item groups
        (setq lst (cdr item))
        (if (> (length lst) 1)
          (progn
            (setq idx 1)
            (while (< idx (length lst))
              (if (radika-guid-set (nth idx lst) (radika-guid-generate))
                (setq fixedDup (1+ fixedDup)))
              (setq idx (1+ idx))))))
      (princ (strcat "\nRADIKA_GUID_REPAIR: lisatty puuttuvat=" (itoa fixedMissing)
                     ", korjattu duplikaatit=" (itoa fixedDup)
                     ", ohitetut=" (itoa skipped) "."))))
  (princ)
)

(princ "\nGUID-TOOLS ladattu. Komennot: RGUID_REFRESH_AUTO / RGUID_AUDIT_AUTO / RGUID_REPAIR_AUTO.")
(princ)
