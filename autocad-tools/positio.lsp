(setq *numero* 0)

(defun c:ASETANUMERO ( / n)
  (setq n (getint "\nAnna aloitusnumero: "))
  (if n (setq *numero* n))
  (princ)
)

;; Etsi positio.lsp:n lataushakemisto. Yritetaan ensin findfile (jos Support
;; Path:lla); muuten luetaan APPLOADin MainDialog-arvo (viimeisin APPLOAD-
;; kansio) jokaiselta AutoCAD-profiililta ja katsotaan loytyyko sielta
;; positio.lsp.
(defun positio-self-folder ( / found regbase target ver prod prof appkey val)
  (vl-load-com)
  (setq target "positio.lsp")
  (cond
    ((setq found (findfile target))
     (vl-filename-directory found))
    (T
     (setq found nil)
     (setq regbase "HKEY_CURRENT_USER\\SOFTWARE\\Autodesk\\AutoCAD")
     (foreach ver (vl-registry-descendents regbase)
       (foreach prod (vl-registry-descendents (strcat regbase "\\" ver))
         (foreach prof (vl-registry-descendents
                         (strcat regbase "\\" ver "\\" prod "\\Profiles"))
           (setq appkey (strcat regbase "\\" ver "\\" prod
                                "\\Profiles\\" prof "\\Dialogs\\Appload"))
           (if (and (not found)
                    (setq val (vl-registry-read appkey "MainDialog"))
                    (= (type val) 'STR)
                    (findfile (strcat val "\\" target)))
             (setq found val))
         )
       )
     )
     found)
  )
)

;; Etsii positio.dwg:n. Prioriteettijarjestys on tarkoituksellinen:
;; ENSIN sama kansio josta positio.lsp ladattiin — positio.dwg matkaa
;; aina positio.lsp:n rinnalla (ZIP-paketti, asennus, repo) — SITTEN
;; vakioasennuspolku %APPDATA%\Radika\Tools.
;;
;; Paljas (findfile "positio.dwg") on POISTETTU: findfile etsii myos
;; avoimen piirustuksen kansiosta, ja jos sielta loytyy haja-positio.dwg
;; joka onkin oikea piirustus (sisaltaa POSITIO-blokin), -INSERT kaatuu
;; "Block POSITIO references itself" -virheeseen. Self-folder antaa aina
;; oikean, paketin mukana tulleen positio.dwg:n.
(defun positio-find-block-file ( / cands self found p)
  (vl-load-com)
  (setq cands '())
  ;; 1. Sama kansio kuin positio.lsp:lla.
  (if (setq self (positio-self-folder))
    (if (= (type self) 'STR)
      (setq cands (list (strcat self "\\positio.dwg")))))
  ;; 2. Vakioasennus (Asenna.cmd kopioi tanne).
  (if (getenv "APPDATA")
    (setq cands (append cands
      (list (strcat (getenv "APPDATA") "\\Radika\\Tools\\positio.dwg")))))
  ;; 3. Vanhat / dev-sijainnit.
  (setq cands (append cands
    (list
      (strcat (getenv "USERPROFILE") "\\suunnittelutyokalut\\positio.dwg")
      (strcat (getenv "USERPROFILE") "\\AutoCADLisp\\positio.dwg")
      "C:\\AutoCADLisp\\positio.dwg")))
  ;; Palauta ensimmainen olemassaoleva.
  (foreach p cands
    (if (and (not found) (= (type p) 'STR) (vl-file-systime p))
      (setq found p)))
  found
)

;; Diagnostic command — printtaa mita positio-find-block-file palauttaa.
;; Aja "POSDEBUG" kommandiriviltä jos POSITIO ei loyda DWG:ta.
(defun c:POSDEBUG ( / s b)
  (princ (strcat "\nDWGPREFIX = " (vl-princ-to-string (getvar "DWGPREFIX"))))
  (princ (strcat "\nUSERPROFILE = " (vl-princ-to-string (getenv "USERPROFILE"))))
  (princ (strcat "\nfindfile positio.lsp = " (vl-princ-to-string (findfile "positio.lsp"))))
  (princ (strcat "\nfindfile positio.dwg = " (vl-princ-to-string (findfile "positio.dwg"))))
  (setq s (positio-self-folder))
  (princ (strcat "\npositio-self-folder = " (vl-princ-to-string s)))
  (setq b (positio-find-block-file))
  (princ (strcat "\npositio-find-block-file = " (vl-princ-to-string b)))
  (princ)
)

;; Kavele insertin sub-entiteetit entnext:lla ja paivita ensimmaisen
;; numero-attribuutin teksti. Tukee tilanteita joissa vla-API ei nae
;; attribuutteja suoraan.
(defun positio-update-attribs-via-entnext ( insEnt / ent ed)
  (setq ent (entnext insEnt))
  (while ent
    (setq ed (entget ent))
    (if (and (= (cdr (assoc 0 ed)) "ATTRIB")
             (member (strcase (cdr (assoc 2 ed)))
                     '("NUMERO" "NRO" "NUM" "POSITIO" "POS" "POSITION")))
      (entmod (subst (cons 1 (itoa *numero*)) (assoc 1 ed) ed))
    )
    (setq ent (entnext ent))
  )
)

(defun c:POSITIO ( / pt blockName blockPath firstTime
                     savedAttreq savedAttdia savedCmddia savedFiledia savedExpert
                     doc ms ins tag)
  (vl-load-com)
  ;; ATTREQ/ATTDIA pidetaan koko komennon ajan koska vla-InsertBlock + entmod
  ;; tarvitsevat hiljaisen attribuutti-promptin ettei dialog avaudu.
  (setq savedAttreq  (getvar "ATTREQ"))
  (setq savedAttdia  (getvar "ATTDIA"))
  (setvar "ATTREQ" 0)
  (setvar "ATTDIA" 0)

  (setq blockName "POSITIO")
  (setq firstTime (not (tblsearch "BLOCK" blockName)))
  (setq blockPath (if firstTime (positio-find-block-file)))

  (if (and firstTime (not blockPath))
    (progn
      (princ "\nVIRHE: positio.dwg ei loydy. Varmista etta positio.dwg on samassa kansiossa kuin positio.lsp.")
      (setvar "ATTREQ" savedAttreq)
      (setvar "ATTDIA" savedAttdia)
      (exit)
    )
  )

  ;; Lataa block-maaritelma kerran origin:iin ja poista valittomasti.
  ;; FILEDIA/CMDDIA/EXPERT vaihdetaan vain talle kapealle blokille jotta
  ;; -INSERT ei avaa file dialogia, ja palautetaan heti perään.
  ;; vl-catch-all-apply takaa palautuksen vaikka -INSERT epaonnistuisi —
  ;; muuten FILEDIA jaisi 0 ja kayttajan SAVE/OPEN-dialogit eivat
  ;; aukaisi ennen kuin manuaalisesti FILEDIA 1.
  (if firstTime
    (progn
      (setq savedCmddia  (getvar "CMDDIA"))
      (setq savedFiledia (getvar "FILEDIA"))
      (setq savedExpert  (getvar "EXPERT"))
      (setvar "CMDDIA"  0)
      (setvar "FILEDIA" 0)
      (setvar "EXPERT"  5)
      (vl-catch-all-apply
        '(lambda ()
           (command "_.-INSERT" (strcat blockName "=" blockPath) "0,0,0" 1 1 0)
           (if (entlast) (entdel (entlast)))))
      (setvar "CMDDIA"  savedCmddia)
      (setvar "FILEDIA" savedFiledia)
      (setvar "EXPERT"  savedExpert)
    )
  )

  (setq doc (vla-get-ActiveDocument (vlax-get-acad-object)))
  (setq ms  (vla-get-ModelSpace doc))

  (while (setq pt (getpoint "\nValitse sijainti (ESC lopettaa): "))
    (setq *numero* (1+ *numero*))

    (setq ins (vla-InsertBlock ms (vlax-3d-point pt) blockName 1.0 1.0 1.0 0.0))

    (if (= (vla-get-HasAttributes ins) :vlax-true)
      (foreach att (vlax-invoke ins 'GetAttributes)
        (setq tag (strcase (vla-get-TagString att)))
        (if (member tag '("NUMERO" "NRO" "NUM" "POSITIO" "POS" "POSITION"))
          (vla-put-TextString att (itoa *numero*))
        )
      )
      ;; Ei suoria attribuutteja — kokeile entnext-fallbackia (nested-rakenteille)
      (positio-update-attribs-via-entnext (vlax-vla-object->ename ins))
    )

    (princ (strcat "\nLisätty numero: " (itoa *numero*)))
  )

  ;; Palauta kayttajan sysvarit (FILEDIA/CMDDIA/EXPERT palautettiin jo
  ;; firstTime-blockin paatteeksi vl-catch-all-apply:n jalkeen)
  (setvar "ATTREQ" savedAttreq)
  (setvar "ATTDIA" savedAttdia)
  (princ)
)
