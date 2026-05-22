;;; HOYRYSTIN.LSP - Hoyrystimien insertointikomennot
;;;
;;; Pikakomennot per puhallinmaara (lyhyet ja pitkat aliakset):
;;;   HY1 / HOYR1 -> 1-puhaltimen hoyrystin (hoyrystin-1.dwg)
;;;   HY2 / HOYR2 -> 2-puhaltimen hoyrystin (hoyrystin-2.dwg)
;;;   HY3 / HOYR3 -> 3-puhaltimen hoyrystin (hoyrystin-3.dwg)
;;;
;;; Layer: KYL-HOYRYSTIMET (AutoCAD Color Index 175, RGB 63,63,127).
;;; dxf2ifc:n preprocessing.py kayttaa wildcardia *yrystin* matchaamaan
;;; sekä ä/o että H/h variantit -> IfcEvaporator IFC-eksportissa.
;;;
;;; Komento-flow: APPLOAD -> HOYR1/2/3 -> nayttat lisayspisteen ->
;;; live-preview rotaatio kuin natiivissa INSERT:ssa.
;;;
;;; Block-DWG-tiedostot files/-kansiossa:
;;;   hoyrystin-1.dwg / hoyrystin-2.dwg / hoyrystin-3.dwg

(vl-load-com)

;; Globaali kansio-cache: kayttajan valitsema kansio muistetaan istunnon
;; ajaksi jos locator ei ole loytanyt DWG:ta automaattisesti.
(if (not (boundp '*hoyr-cached-folder*)) (setq *hoyr-cached-folder* nil))

;; Kaapataan LSP:n kansio LOAD-aikaan. Locator kayttaa tata DWG-haussa,
;; jotta tiedostot loytyvat samasta paikasta kuin LSP — missa tahansa
;; ZIP on purettu.
;;
;; Vaiheet:
;;   1. (findfile "hoyrystin.lsp") jos LSP on AutoCAD Support Path:lla
;;   2. Registry HKCU\SOFTWARE\Autodesk\AutoCAD\...\Appload\MainDialog
;;      = viimeisin APPLOAD-kansio. Tarkistetaan etta LSP on siella.

(defun hoyr-find-lsp-folder ( / regbase ver prod prof appkey val found ff )
  (setq found nil)
  (setq ff (findfile "hoyrystin.lsp"))
  (if (and ff (= (type ff) 'STR))
    (setq found (vl-filename-directory ff))
    (progn
      (setq regbase "HKEY_CURRENT_USER\\SOFTWARE\\Autodesk\\AutoCAD")
      (foreach ver (vl-registry-descendents regbase)
        (foreach prod (vl-registry-descendents (strcat regbase "\\" ver))
          (foreach prof (vl-registry-descendents
                          (strcat regbase "\\" ver "\\" prod "\\Profiles"))
            (setq appkey (strcat regbase "\\" ver "\\" prod
                                 "\\Profiles\\" prof "\\Dialogs\\Appload"))
            (setq val (vl-registry-read appkey "MainDialog"))
            (if (and (null found) val (= (type val) 'STR)
                     (vl-file-systime (strcat val "\\hoyrystin.lsp")))
              (setq found val)))))))
  found)

(setq *hoyr-lsp-folder* (hoyr-find-lsp-folder))

;; ============================================================
;; LAYER-HELPER
;; ============================================================

(defun hoyr-ensure-layer ( layerName colorIndex
                            / acadObj doc layers layer )
  (if (null (tblsearch "LAYER" layerName))
    (progn
      (setq acadObj (vlax-get-acad-object))
      (setq doc (vla-get-ActiveDocument acadObj))
      (setq layers (vla-get-Layers doc))
      (setq layer (vla-Add layers layerName))
      (vla-put-Color layer colorIndex)
    )
  )
  layerName
)

;; ============================================================
;; BLOCK-DWG LOCATOR
;; ============================================================
;;
;; Etsii dwgName:n nimisen tiedoston seuraavissa paikoissa
;; jarjestyksessa, ensimmainen olemassaoleva voittaa:
;;   1. AutoCAD Support Path (findfile)
;;   2. Aiemmin file-dialogilla valittu kansio (cached)
;;   3. LSP:n oma kansio (kaapattu LOAD-aikana)
;;   4. Current DWG-kansio (DWGPREFIX)
;;   5. %USERPROFILE%\suunnittelutyokalut\ (yleinen ZIP-purkupaikka)
;; Jos ei loydy -> file-dialog, jonka kansio muistetaan istunnon ajaksi.

;; Hakujarjestys: cached -> hoyrystin.lsp:n oma kansio -> vakioasennus
;; -> yleiset paikat -> findfile -> file-dialog. Paljas findfile on
;; demotettu: se etsii myos avoimen piirustuksen kansiosta, ja
;; samanniminen hajatiedosto kaataisi -INSERTin "block references
;; itself" -virheeseen.
(defun hoyr-find-block-file ( dwgName / cands found p picked )
  (vl-load-com)
  (setq cands '())
  ;; 1. Aiemmin file-dialogilla valittu kansio (cached)
  (if (and *hoyr-cached-folder* (= (type *hoyr-cached-folder*) 'STR))
    (setq cands (list (strcat *hoyr-cached-folder* "\\" dwgName))))
  ;; 2. hoyrystin.lsp:n oma kansio (kaapattu LOAD-aikana)
  (if (and *hoyr-lsp-folder* (= (type *hoyr-lsp-folder*) 'STR))
    (setq cands (append cands
                        (list (strcat *hoyr-lsp-folder* "\\" dwgName)))))
  ;; 3. Vakioasennus (Asenna.cmd kopioi tanne)
  (if (getenv "APPDATA")
    (setq cands (append cands
      (list (strcat (getenv "APPDATA") "\\Radika\\Tools\\" dwgName)))))
  ;; 4. Vanhat / dev-sijainnit
  (setq cands (append cands
    (list
      (strcat (getenv "USERPROFILE") "\\suunnittelutyokalut\\" dwgName)
      (strcat (getenv "USERPROFILE") "\\AutoCADLisp\\" dwgName)
      (strcat "C:\\AutoCADLisp\\" dwgName))))
  (foreach p cands
    (if (and (not found) (= (type p) 'STR) (vl-file-systime p))
      (setq found p)))
  ;; 5. findfile demottuna (Support Path).
  (if (null found)
    (if (setq p (findfile dwgName))
      (if (= (type p) 'STR) (setq found p))))
  ;; 6. Viimeisena: kayttaja valitsee file-dialogilla.
  (if (null found)
    (progn
      (princ (strcat "\n" dwgName " ei loytynyt — valitse kansio file-dialogilla."))
      (setq picked (getfiled (strcat "Etsi " dwgName) dwgName "dwg" 0))
      (if (and picked (= (type picked) 'STR))
        (progn
          (setq found picked)
          (setq *hoyr-cached-folder* (vl-filename-directory picked))
          (princ "\nKansio muistettu istunnon ajaksi.")))))
  found
)

;; ============================================================
;; BLOCK-DEFINITION LOADER
;; ============================================================

(defun hoyr-ensure-block ( blockName dwgFileName / dwgPath )
  (if (tblsearch "BLOCK" blockName)
    T
    (progn
      (setq dwgPath (hoyr-find-block-file dwgFileName))
      (if (or (null dwgPath) (not (= (type dwgPath) 'STR)))
        (progn
          (princ (strcat "\nVIRHE: " dwgFileName " ei loydy."))
          (princ "\nTarkista etta hoyrystin-*.dwg-tiedostot ovat samassa kansiossa")
          (princ "\nkuin hoyrystin.lsp tai $USERPROFILE\\suunnittelutyokalut\\.")
          nil)
        (progn
          (command "_.-INSERT" (strcat blockName "=" dwgPath))
          (command)
          T))))
)

;; ============================================================
;; PAAKOMENTO: insert hoyrystin
;; ============================================================

(defun hoyr-insert ( puh / *error* oldClayer oldCmdecho oldOsmode
                          blockName dwgName ok )

  (defun *error* ( msg )
    (if oldOsmode  (setvar "OSMODE"  oldOsmode))
    (if oldCmdecho (setvar "CMDECHO" oldCmdecho))
    (if oldClayer  (setvar "CLAYER"  oldClayer))
    (if (and msg (not (wcmatch (strcase msg) "*CANCEL*,*ABORT*,*EXIT*")))
      (princ (strcat "\nVirhe: " msg)))
    (princ))

  (setq oldClayer  (getvar "CLAYER"))
  (setq oldCmdecho (getvar "CMDECHO"))
  (setq oldOsmode  (getvar "OSMODE"))

  (hoyr-ensure-layer "KYL-HOYRYSTIMET" 175)   ; ACI 175 (RGB 63,63,127)

  (setq blockName (strcat "HOYRYSTIN-" (itoa puh) "PUH"))
  (setq dwgName   (strcat "hoyrystin-" (itoa puh) ".dwg"))

  (setq ok (hoyr-ensure-block blockName dwgName))
  (if (null ok) (exit))

  (setvar "CLAYER" "KYL-HOYRYSTIMET")
  (setvar "CMDECHO" 0)

  ;; Anna AutoCAD:n hoitaa INSERT-prompts interaktiivisesti — kayttaja
  ;; saa live-preview kun pyorittaa rotaatiota.
  (command "_.-INSERT" blockName pause 1 1 pause)

  (setvar "OSMODE"  oldOsmode)
  (setvar "CMDECHO" oldCmdecho)
  (setvar "CLAYER"  oldClayer)
  (princ (strcat "\n" blockName " luotu.")))

;; ============================================================
;; KAYTTAJAN KOMENNOT
;; ============================================================

;; Lyhyet pikakomennot
(defun c:HY1 ( / ) (hoyr-insert 1))
(defun c:HY2 ( / ) (hoyr-insert 2))
(defun c:HY3 ( / ) (hoyr-insert 3))

;; Pidemmat aliakset (taaksepain yhteensopivuus)
(defun c:HOYR1 ( / ) (hoyr-insert 1))
(defun c:HOYR2 ( / ) (hoyr-insert 2))
(defun c:HOYR3 ( / ) (hoyr-insert 3))

(princ "\nHOYRYSTIN ladattu. Komennot: HY1, HY2, HY3 (tai HOYR1/2/3).")
(princ)
