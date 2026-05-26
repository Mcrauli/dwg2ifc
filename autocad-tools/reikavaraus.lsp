;;; REIKAVARAUS.LSP - Reikavarausblockin insertointi
;;;
;;; Komennot:
;;;   REIKAVARAUS / RV -> luo ja sijoittaa REIKAVARAUS-blockin layerille
;;;                       KYL-REIKAVARAUS
;;;
;;; Blockin ATTRIB-tagit on tehty parserin odotusten mukaan:
;;;   GUID, VARAUS_TYYPPI, HALKAISIJA, PITUUS, KORKO, VARAAJA, TUNNUS, KOMMENTTI
;;; GUID generoidaan automaattisesti (UUIDv4-muotoinen) joka uuteen varaukseen.
;;; Lisäksi luodaan 3D-sylinteri suoraan layerille KYL-REIKAVARAUS.

(vl-load-com)

(if (not (boundp '*rv-last-type*))      (setq *rv-last-type* "LATTIA"))
(if (not (boundp '*rv-last-dia*))       (setq *rv-last-dia* 200.0))
(if (not (boundp '*rv-last-depth*))     (setq *rv-last-depth* 300.0))
(if (not (boundp '*rv-last-overrun*))   (setq *rv-last-overrun* 0.0))

(defun rv-ensure-layer ( layerName colorIndex / acadObj doc layers layer )
  (if (null (tblsearch "LAYER" layerName))
    (progn
      (setq acadObj (vlax-get-acad-object))
      (setq doc (vla-get-ActiveDocument acadObj))
      (setq layers (vla-get-Layers doc))
      (setq layer (vla-Add layers layerName))
      (vla-put-Color layer colorIndex)))
  layerName
)

(defun rv-rand32 ( / seed )
  (if (not (boundp '*rv-seed*))
    (setq *rv-seed* (fix (* 1000000.0 (rem (getvar "DATE") 1.0)))))
  (setq seed (rem (+ (* *rv-seed* 1664525.0) 1013904223.0) 4294967296.0))
  (setq *rv-seed* seed)
  seed
)

(defun rv-hex-char ( n )
  (substr "0123456789abcdef" (1+ n) 1)
)

(defun rv-rand-hex ( n / i out )
  (setq i 0 out "")
  (while (< i n)
    (setq out (strcat out (rv-hex-char (fix (rem (rv-rand32) 16.0)))))
    (setq i (1+ i)))
  out
)

(defun rv-generate-guid ( / y )
  (setq y (+ 8 (fix (rem (rv-rand32) 4.0))))
  (strcat
    (rv-rand-hex 8) "-"
    (rv-rand-hex 4) "-4"
    (rv-rand-hex 3) "-"
    (rv-hex-char y)
    (rv-rand-hex 3) "-"
    (rv-rand-hex 12))
)

(defun rv-entmake-attdef ( tag prompt def pt / )
  (entmake
    (list
      (cons 0 "ATTDEF")
      (cons 8 "0")
      (cons 10 pt)
      (cons 40 2.5)
      (cons 1 def)
      (cons 3 prompt)
      (cons 2 tag)
      (cons 70 1)
      (cons 72 0)
      (cons 74 0)))
)

(defun rv-ensure-block-def ( / )
  (if (null (tblsearch "BLOCK" "REIKAVARAUS"))
    (progn
      (entmake
        (list
          (cons 0 "BLOCK")
          (cons 2 "REIKAVARAUS")
          (cons 70 2)
          (cons 10 '(0.0 0.0 0.0))))
      (entmake
        (list
          (cons 0 "CIRCLE")
          (cons 8 "0")
          (cons 10 '(0.0 0.0 0.0))
          (cons 40 100.0)))
      (rv-entmake-attdef "GUID" "GUID" "" '(130.0 90.0 0.0))
      (rv-entmake-attdef "VARAUS_TYYPPI" "Varaustyyppi" "LATTIA" '(130.0 80.0 0.0))
      (rv-entmake-attdef "HALKAISIJA" "Halkaisija" "200" '(130.0 70.0 0.0))
      (rv-entmake-attdef "PITUUS" "Pituus" "300" '(130.0 60.0 0.0))
      (rv-entmake-attdef "KORKO" "Korko" "0" '(130.0 50.0 0.0))
      (rv-entmake-attdef "VARAAJA" "Varaaja" "KYL" '(130.0 40.0 0.0))
      (rv-entmake-attdef "TUNNUS" "Tunnus" "" '(130.0 30.0 0.0))
      (rv-entmake-attdef "KOMMENTTI" "Kommentti" "" '(130.0 20.0 0.0))
      (entmake (list (cons 0 "ENDBLK")))))
  "REIKAVARAUS"
)

(defun rv-set-attr ( blockRef tag value / atts i a )
  (setq atts (vlax-invoke blockRef 'GetAttributes))
  (setq i 0)
  (while (< i (length atts))
    (setq a (nth i atts))
    (if (= (strcase (vla-get-TagString a)) (strcase tag))
      (vla-put-TextString a value))
    (setq i (1+ i)))
)

(defun rv-point-along-xy ( p1 ang dist / )
  (list
    (+ (car p1) (* dist (cos ang)))
    (+ (cadr p1) (* dist (sin ang)))
    (caddr p1))
)

(defun rv-point-shift-xy ( p1 ang dist / )
  (list
    (+ (car p1) (* dist (cos ang)))
    (+ (cadr p1) (* dist (sin ang)))
    (caddr p1))
)

(defun rv-ensure-regapp ( app / )
  (if (null (tblsearch "APPID" app))
    (entmake (list (cons 0 "APPID") (cons 2 app) (cons 70 0))))
  app
)

(defun rv-write-solid-xdata ( ent extras / xd )
  (if (and ent (entget ent))
    (progn
      (rv-ensure-regapp "RADIKA_REIKAVARAUS")
      (setq xd
        (list
          (list -3
            (list
              "RADIKA_REIKAVARAUS"
              (cons 1000 (strcat "GUID=" (cdr (assoc "GUID" extras))))
              (cons 1000 (strcat "VARAUS_TYYPPI=" (cdr (assoc "VARAUS_TYYPPI" extras))))
              (cons 1000 (strcat "HALKAISIJA=" (cdr (assoc "HALKAISIJA" extras))))
              (cons 1000 (strcat "PITUUS=" (cdr (assoc "PITUUS" extras))))
              (cons 1000 (strcat "YLITYS_MM=" (cdr (assoc "YLITYS_MM" extras))))
              (cons 1000 (strcat "KULMA_RAD=" (cdr (assoc "KULMA_RAD" extras))))
              (cons 1000 (strcat "KORKO=" (cdr (assoc "KORKO" extras))))
              (cons 1000 (strcat "VARAAJA=" (cdr (assoc "VARAAJA" extras))))
              (cons 1000 (strcat "TUNNUS=" (cdr (assoc "TUNNUS" extras))))
              (cons 1000 (strcat "KOMMENTTI=" (cdr (assoc "KOMMENTTI" extras))))))))
      (vl-catch-all-apply 'entmod (list (append (entget ent) xd))))))

(defun rv-insert ( / *error* oldClayer oldCmdecho oldOsmode oldAttreq oldAttdia
                      typ dia dep p1 p2 ang guid axisEnd zIn zAbs solid meta
                      overrun startPt tunnus kommentti )
  (defun *error* ( msg )
    (if oldAttdia  (setvar "ATTDIA" oldAttdia))
    (if oldAttreq  (setvar "ATTREQ" oldAttreq))
    (if oldOsmode  (setvar "OSMODE" oldOsmode))
    (if oldCmdecho (setvar "CMDECHO" oldCmdecho))
    (if oldClayer  (setvar "CLAYER" oldClayer))
    (if (and msg (not (wcmatch (strcase msg) "*CANCEL*,*ABORT*,*EXIT*")))
      (princ (strcat "\nVirhe: " msg)))
    (princ))

  (setq oldClayer  (getvar "CLAYER"))
  (setq oldCmdecho (getvar "CMDECHO"))
  (setq oldOsmode  (getvar "OSMODE"))
  (setq oldAttreq  (getvar "ATTREQ"))
  (setq oldAttdia  (getvar "ATTDIA"))

  (setvar "CMDECHO" 0)
  (setvar "ATTREQ" 0)
  (setvar "ATTDIA" 0)

  (rv-ensure-layer "KYL-REIKAVARAUS" 175)

  (initget "LATTIA SEINA")
  (setq typ (getkword (strcat "\nVaraustyyppi [LATTIA/SEINA] <" *rv-last-type* ">: ")))
  (if (null typ) (setq typ *rv-last-type*))
  (setq *rv-last-type* typ)

  (setq dia (getreal (strcat "\nHalkaisija (mm) <" (rtos *rv-last-dia* 2 0) ">: ")))
  (if (null dia) (setq dia *rv-last-dia*))
  (if (<= dia 0.0) (setq dia *rv-last-dia*))
  (setq *rv-last-dia* dia)

  (setq dep (getreal (strcat "\nPituus (mm) <" (rtos *rv-last-depth* 2 0) ">: ")))
  (if (null dep) (setq dep *rv-last-depth*))
  (if (<= dep 0.0) (setq dep *rv-last-depth*))
  (setq *rv-last-depth* dep)

  (setq overrun (getreal (strcat "\nTorrotys per puoli (mm) <" (rtos *rv-last-overrun* 2 0) ">: ")))
  (if (null overrun) (setq overrun *rv-last-overrun*))
  (if (< overrun 0.0) (setq overrun *rv-last-overrun*))
  (setq *rv-last-overrun* overrun)

  (setq p1 (getpoint "\nAsetuspiste: "))
  (if (null p1) (exit))
  (setq zIn (getreal (strcat "\nKorko Z (mm) <" (rtos (caddr p1) 2 0) ">: ")))
  (setq zAbs (if (null zIn) (caddr p1) zIn))
  (setq p1 (list (car p1) (cadr p1) zAbs))
  (setq tunnus "")
  (setq kommentti "")

  (setq ang 0.0)
  (if (= (strcase typ) "SEINA")
    (progn
      (setq p2 (getpoint p1 "\nValitse seinavaraussuunnan piste: "))
      (if p2 (setq ang (angle p1 p2)))))

  (setq guid (rv-generate-guid))

  ;; 3D-runko CADiin: lattia = +Z, seina = valittu suunta XY:ssa.
  (setvar "CLAYER" "KYL-REIKAVARAUS")
  (if (= (strcase typ) "SEINA")
    (progn
      (setq startPt (rv-point-shift-xy p1 ang (- overrun)))
      (setq axisEnd (rv-point-along-xy p1 ang (+ dep overrun))))
    (progn
      (setq startPt (list (car p1) (cadr p1) (- (caddr p1) overrun)))
      (setq axisEnd (list (car p1) (cadr p1) (+ (caddr p1) dep overrun)))))
  (command "_.CYLINDER" startPt "_D" dia "_A" axisEnd)
  (setq solid (entlast))
  (if solid
    (progn
      (setq meta
        (list
          (cons "GUID" guid)
          (cons "VARAUS_TYYPPI" (strcase typ))
          (cons "HALKAISIJA" (rtos dia 2 0))
          (cons "PITUUS" (rtos dep 2 0))
          (cons "YLITYS_MM" (rtos overrun 2 0))
          (cons "KULMA_RAD" (rtos ang 2 8))
          (cons "KORKO" (rtos (caddr p1) 2 0))
          (cons "VARAAJA" "KYL")
          (cons "TUNNUS" tunnus)
          (cons "KOMMENTTI" kommentti)))
      (rv-write-solid-xdata solid meta)))

  (setvar "ATTDIA" oldAttdia)
  (setvar "ATTREQ" oldAttreq)
  (setvar "OSMODE" oldOsmode)
  (setvar "CMDECHO" oldCmdecho)
  (setvar "CLAYER" oldClayer)

  (princ (strcat "\nREIKAVARAUS luotu. GUID: " guid))
  (princ)
)

(defun c:REIKAVARAUS ( / ) (rv-insert))
(defun c:RV          ( / ) (rv-insert))

(princ "\nREIKAVARAUS ladattu. Komento: REIKAVARAUS (tai RV).")
(princ)
