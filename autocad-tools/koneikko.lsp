;;; KONEIKKO.LSP - Kylmakoneikon insertointikomento
;;;
;;; Komennot:
;;;   KONEIKKO / KKO -> sijoittaa Koneikko.dwg-blockin live-preview-
;;;                     rotaatiolla kuten natiivi INSERT
;;;
;;; Layer: KYL-KONEIKKO (AutoCAD Color Index 175, RGB 63,63,127) - sama
;;; vari kuin muilla KYL-tyokaluilla. dxf2ifc tunnistaa KYL-KONEIKKO*-
;;; layerin -> IfcUnitaryEquipment IFC-eksportissa.
;;;
;;; Block-DWG samassa kansiossa kuin tama LSP: Koneikko.dwg
;;;
;;; Lataa: APPLOAD -> valitse tama tiedosto.

(vl-load-com)

;; Globaali kansio-cache: kayttajan valitsema kansio muistetaan istunnon
;; ajaksi jos locator ei ole loytanyt DWG:ta automaattisesti.
(if (not (boundp '*koneikko-cached-folder*)) (setq *koneikko-cached-folder* nil))

;; Kaapataan LSP:n kansio LOAD-aikaan. Locator kayttaa tata DWG-haussa.
(defun koneikko-find-lsp-folder ( / regbase ver prod prof appkey val found ff )
  (setq found nil)
  (setq ff (findfile "koneikko.lsp"))
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
                     (vl-file-systime (strcat val "\\koneikko.lsp")))
              (setq found val)))))))
  found)

(setq *koneikko-lsp-folder* (koneikko-find-lsp-folder))

;; ============================================================
;; LAYER-HELPER
;; ============================================================

(defun koneikko-ensure-layer ( layerName colorIndex
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
;; Hakujarjestys:
;;   1. *radika-lsp-dir*  (asentajan asettama Tools-polku) — ENSISIJAINEN
;;      jotta projektikansion samannimiset DWG:t (esim. vanha
;;      Koneikko.dwg toisesta projektista) eivat varasta hakua.
;;   2. *koneikko-lsp-folder* (LSP:n oma kansio)
;;   3. *koneikko-cached-folder* (session aikana muistettu)
;;   4. findfile (Support Path -haku)
;;   5. DWGPREFIX (nykyisen DWG:n kansio)
;;   6. %USERPROFILE%\suunnittelutyokalut\
;;   7. file-dialog viimeisena fallback:na

(defun koneikko-find-block-file ( dwgName / cands prefix found p picked ff )
  (vl-load-com)
  (setq found nil)
  (setq cands '())
  ;; 1. ENSISIJAINEN: asentajan asettama Tools-polku
  (if (and (boundp '*radika-lsp-dir*) *radika-lsp-dir*
           (= (type *radika-lsp-dir*) 'STR))
    (setq cands (list (strcat *radika-lsp-dir* dwgName))))
  ;; 2. LSP-kansio
  (if (and *koneikko-lsp-folder* (= (type *koneikko-lsp-folder*) 'STR))
    (setq cands (append cands
                        (list (strcat *koneikko-lsp-folder* "\\" dwgName)))))
  ;; 3. Session cached folder
  (if (and *koneikko-cached-folder* (= (type *koneikko-cached-folder*) 'STR))
    (setq cands (append cands
                        (list (strcat *koneikko-cached-folder* "\\" dwgName)))))
  ;; Etsi ensimmainen joka on olemassa
  (foreach p cands
    (if (and (not found) (= (type p) 'STR) (vl-file-systime p))
      (setq found p)))
  ;; 4. findfile (Support Path)
  (if (null found)
    (progn
      (setq ff (findfile dwgName))
      (if (and ff (= (type ff) 'STR)) (setq found ff))))
  ;; 5. DWGPREFIX
  (if (null found)
    (progn
      (setq prefix (getvar "DWGPREFIX"))
      (if (and prefix (= (type prefix) 'STR) (> (strlen prefix) 0)
               (vl-file-systime (strcat prefix dwgName)))
        (setq found (strcat prefix dwgName)))))
  ;; 6. USERPROFILE
  (if (null found)
    (progn
      (setq p (strcat (getenv "USERPROFILE") "\\suunnittelutyokalut\\" dwgName))
      (if (vl-file-systime p) (setq found p))))
  ;; 7. file-dialog
  (if (null found)
    (progn
      (princ (strcat "\n" dwgName " ei loytynyt - valitse kansio file-dialogilla."))
      (setq picked (getfiled (strcat "Etsi " dwgName) dwgName "dwg" 0))
      (if (and picked (= (type picked) 'STR))
        (progn
          (setq found picked)
          (setq *koneikko-cached-folder* (vl-filename-directory picked))
          (princ "\nKansio muistettu istunnon ajaksi.")))))
  found
)

;; ============================================================
;; BLOCK-DEFINITION LOADER
;; ============================================================

;; Aina pakota block-maarityksen lataus polusta — varmistaa etta
;; ATTDEF:n / geometrian / varin paivitykset DWG:hen naky vat ilman
;; etta kayttajan tarvitsee manuaalisesti redefinetada blockia. Jos
;; block oli jo maaritetty tassa piirustuksessa, "_Y" vastaa AutoCAD:n
;; "Redefine block?"-promptiin. Tyhja (command) cancel-tekee INSERT:n
;; nopeasti niin etta vain block-maaritys paivittyy — paakomento luo
;; instanssin erikseen.
(defun koneikko-ensure-block ( blockName dwgFileName / dwgPath isRedefine )
  (setq dwgPath (koneikko-find-block-file dwgFileName))
  (if (or (null dwgPath) (not (= (type dwgPath) 'STR)))
    (progn
      (princ (strcat "\nVIRHE: " dwgFileName " ei loydy."))
      (princ "\nTarkista etta Koneikko.dwg on samassa kansiossa kuin")
      (princ "\nkoneikko.lsp tai $USERPROFILE\\suunnittelutyokalut\\.")
      nil)
    (progn
      (setq isRedefine (if (tblsearch "BLOCK" blockName) T nil))
      (command "_.-INSERT" (strcat blockName "=" dwgPath))
      (if isRedefine (command "_Y"))   ; "Redefine block?" -> Yes
      (command)                         ; cancel INSERT instance
      T))
)

;; ============================================================
;; PAAKOMENTO: insert koneikko
;; ============================================================

(defun koneikko-insert ( / *error* oldClayer oldCmdecho oldOsmode
                             oldAttreq oldAttdia
                             blockName dwgName ok )

  (defun *error* ( msg )
    (if oldAttdia  (setvar "ATTDIA"  oldAttdia))
    (if oldAttreq  (setvar "ATTREQ"  oldAttreq))
    (if oldOsmode  (setvar "OSMODE"  oldOsmode))
    (if oldCmdecho (setvar "CMDECHO" oldCmdecho))
    (if oldClayer  (setvar "CLAYER"  oldClayer))
    (if (and msg (not (wcmatch (strcase msg) "*CANCEL*,*ABORT*,*EXIT*")))
      (princ (strcat "\nVirhe: " msg)))
    (princ))

  (setq oldClayer  (getvar "CLAYER"))
  (setq oldCmdecho (getvar "CMDECHO"))
  (setq oldOsmode  (getvar "OSMODE"))
  (setq oldAttreq  (getvar "ATTREQ"))
  (setq oldAttdia  (getvar "ATTDIA"))

  (koneikko-ensure-layer "KYL-KONEIKKO" 175)   ; ACI 175 (RGB 63,63,127)

  (setq blockName "KONEIKKO")
  (setq dwgName   "Koneikko.dwg")

  (setq ok (koneikko-ensure-block blockName dwgName))
  (if (null ok) (exit))

  (setvar "CLAYER" "KYL-KONEIKKO")
  (setvar "CMDECHO" 0)
  ;; Pakota attribuuttien kysely INSERT:in yhteydessa. ATTREQ=1 vaatii
  ;; niiden tayttamista, ATTDIA=1 avaa dialog-ikkunan (muuten kysytaan
  ;; rivi riveltä komentorivilla). Kayttajan kone-asetukset palautetaan
  ;; lopussa / *error*-haarassa.
  (setvar "ATTREQ" 1)
  (setvar "ATTDIA" 1)

  ;; Anna AutoCAD:n hoitaa INSERT-prompts interaktiivisesti — kayttaja
  ;; saa live-preview kun pyorittaa rotaatiota. "_S" 1 lukitsee skaalan
  ;; heti, while-pause -loop luovuttaa loput (insertointipiste + rotaatio)
  ;; kayttajalle. Toimii seka AutoCAD etta BricsCAD vaikka niiden
  ;; -INSERT-prompt-sekvenssi muuten eroaa (sama kuvio kuin varusteet.lsp).
  (command "_.-INSERT" blockName "_S" 1)
  (while (= 1 (logand 1 (getvar "CMDACTIVE")))
    (command pause))

  (setvar "ATTDIA"  oldAttdia)
  (setvar "ATTREQ"  oldAttreq)
  (setvar "OSMODE"  oldOsmode)
  (setvar "CMDECHO" oldCmdecho)
  (setvar "CLAYER"  oldClayer)
  (princ "\nKONEIKKO luotu."))

;; ============================================================
;; KAYTTAJAN KOMENNOT
;; ============================================================

(defun c:KONEIKKO ( / ) (koneikko-insert))
(defun c:KKO      ( / ) (koneikko-insert))

(princ "\nKONEIKKO ladattu. Komento: KONEIKKO (tai KKO).")
(princ)
