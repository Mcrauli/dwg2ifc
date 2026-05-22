;;; VARUSTEET.LSP - Kylmakoneikon sahkovarustelun blockit
;;;
;;; Riippuvuus: rinnalla files/ -kansiossa kuusi DWG-tiedostoa:
;;;   co2-anturi.dwg         - CO2-vuotoanturi
;;;   co2-sireeni.dwg        - CO2-halytinsireeni
;;;   huolto-pc.dwg          - Huolto-PC tai valvomotyoasema
;;;   rk-jk10.dwg            - Ryhmakeskus (esimerkki JK10)
;;;   saadinkeskus-ku.dwg    - Saadinkeskus (kontrolliyksikko)
;;;   hataseispainike.dwg    - Kylmakoneikon hatdiseispainike
;;;
;;; Lataa: APPLOAD -> tama tiedosto. (DWG:t loydetaan automaattisesti
;;; samasta kansiosta josta varusteet.lsp ladataan, vastaavaan tapaan
;;; kuin klhylly.lsp / positio.lsp tekevat omille block-DWG:lleen.)
;;;
;;; Komento:
;;;   VARUSTEET
;;;     -> keyword-prompti: CO2anturi / CO2sireeni / HuoltoPC /
;;;        RKJK10 / Saadinkeskus / Hataseis (nuolinappaimet)
;;;     -> insertointipiste pickilla
;;;     -> rotaatio pickilla tai numerona
;;;
;;; Layerit luodaan automaattisesti per laite (KYL-CO2-ANTURI,
;;; KYL-CO2-SIREENI, KYL-HUOLTO-PC, KYL-RK-JK10, KYL-SAADINKESKUS-KU,
;;; KYL-HATASEIS), kaikki AutoCAD Color Index 175 (RGB 63,63,127).
;;; Block-maaritysten sisalla geometria
;;; on layerilla 0 (BYBLOCK), joten instanssin layer periytyy alaspain
;;; ja dxf2ifc tunnistaa laitetyypin layer-pattern-mappauksesta.
;;;
;;; dxf2ifc-mappaus (default_kylmalaite.toml, v0.2.0a19+):
;;;   KYL-CO2-ANTURI*       -> IfcSensor / CO2SENSOR
;;;   KYL-CO2-SIREENI*      -> IfcAlarm / SIREN
;;;   KYL-HUOLTO-PC*        -> IfcCommunicationsAppliance / COMPUTER
;;;   KYL-RK-*              -> IfcElectricDistributionBoard / DISTRIBUTIONBOARD
;;;   KYL-SAADINKESKUS-*    -> IfcController / PROGRAMMABLE
;;;   KYL-HATASEIS*         -> IfcSwitchingDevice / EMERGENCYSTOP
;;;
;;; Kaikkien RAVA-koodi on T-TATE-02-01-003 (Tilavaraus - laitteisto)
;;; tai T-TATE-02-01-004 (Tilavaraus - keskus): kylmasuunnittelija
;;; varaa tilan, sahkdosuunnittelija korvaa lopullisella laitteella.

(vl-load-com)

;; ============================================================
;; LAITTEIDEN MAPPAUS
;; ============================================================
;;
;; Lista per laite:
;;   (keyword dwg-filename acad-block-name target-layer-name aci-color)
;;
;; - keyword on getkword-valikon nimi (ASCII, ei valilyonteja).
;; - dwg-filename loaytetaan samasta kansiosta kuin varusteet.lsp.
;; - acad-block-name on nimi jolla -INSERT lataa blockin AutoCAD:in
;;   block-tauluun. Sama session yli (uudelleenkutsu ei lataa
;;   blokkia uudelleen jos se on jo blocks-taulussa).
;; - target-layer-name luodaan automaattisesti puuttuessaan annetulla
;;   ACI-varilla. Olemassaolevaan layeriin ei kosketa.

;; Keyword-avaimet on valittu niin etta jokaisella on UNIIKKI ekakirjain
;; (A/S/P/R/K/H). Aiemmat "CO2anturi" ja "CO2sireeni" lyhentyivat initget:ssa
;; molemmat "CO":ksi -> getkword sekosi kun kayttaja nappaili lyhennetta.
;; ACI 175 (RGB 63,63,127) kaikille — yhtenainen KYL-varikonventio,
;; sama vari jonka dxf2ifc emittoi IFC:hen (Solibri-yhdenmukaisuus).
(setq varusteet-device-map
  (list
    (list "Anturi"      "co2-anturi.dwg"        "CO2-anturi"       "KYL-CO2-ANTURI"        175)
    (list "Sireeni"     "co2-sireeni.dwg"       "CO2-sireeni"      "KYL-CO2-SIREENI"       175)
    (list "Pc"          "huolto-pc.dwg"         "Huolto-PC"        "KYL-HUOLTO-PC"         175)
    (list "Ryhmakeskus" "rk-jk10.dwg"           "RK-JK10"          "KYL-RK-JK10"           175)
    (list "Keskus"      "saadinkeskus-ku.dwg"   "Saadinkeskus-KU"  "KYL-SAADINKESKUS-KU"   175)
    (list "Hataseis"    "hataseispainike.dwg"   "Hataseispainike"  "KYL-HATASEIS"          175)
  )
)

;; ============================================================
;; LAYER HELPER
;; ============================================================

;; Varmistaa etta layer on olemassa annetulla AutoCAD color index:lla.
;; Jos layer on jo olemassa, ei kosketa sen asetuksiin (kayttajan
;; custom-vari sailyy).
(defun varusteet-ensure-layer ( layerName colorIndex
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
;; SELF-FOLDER + BLOCK-DWG LOCATOR
;; ============================================================
;;
;; Sama strategia kuin klhylly.lsp:n vastaavissa funktioissa:
;; etsi paasta varusteet.lsp:n sijainti -> sisterns DWG:t loytyvat
;; samasta kansiosta. Fallback yleisiin polkuihin
;; (suunnittelutyokalut, AutoCADLisp).

(defun varusteet-self-folder ( / found regbase target ver prod prof appkey val )
  (vl-load-com)
  (setq target "varusteet.lsp")
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

;; Hakujarjestys: ENSIN varusteet.lsp:n oma kansio (DWG:t matkaavat
;; LSP:n rinnalla — ZIP, asennus, repo), sitten vakioasennus. Paljas
;; findfile on demotettu viimeiseksi: se etsii myos avoimen piirustuksen
;; kansiosta, ja samanniminen hajatiedosto kaataisi -INSERTin "block
;; references itself" -virheeseen.
(defun varusteet-find-block-file ( dwgName / cands self found p )
  (vl-load-com)
  (setq cands '())
  ;; 1. varusteet.lsp:n oma kansio.
  (if (setq self (varusteet-self-folder))
    (if (= (type self) 'STR)
      (setq cands (list (strcat self "\\" dwgName)))))
  ;; 2. Vakioasennus (Asenna.cmd kopioi tanne).
  (if (getenv "APPDATA")
    (setq cands (append cands
      (list (strcat (getenv "APPDATA") "\\Radika\\Tools\\" dwgName)))))
  ;; 3. Vanhat / dev-sijainnit.
  (setq cands (append cands
    (list
      (strcat (getenv "USERPROFILE") "\\suunnittelutyokalut\\" dwgName)
      (strcat (getenv "USERPROFILE") "\\AutoCADLisp\\" dwgName)
      (strcat "C:\\AutoCADLisp\\" dwgName))))
  (foreach p cands
    (if (and (not found) (= (type p) 'STR) (vl-file-systime p))
      (setq found p)))
  ;; 4. Viimeinen oljenkorsi: findfile (Support Path).
  (if (null found)
    (if (setq p (findfile dwgName))
      (if (= (type p) 'STR) (setq found p))))
  found
)

;; ============================================================
;; VARUSTEET-KOMENTO
;; ============================================================

(defun c:VARUSTEET ( / *error* oldClayer oldCmdecho oldOsmode oldDynmode
                       choice entry dwgName blockName layerName colorIndex
                       blockPath firstTime savedFiledia savedCmddia savedExpert )

  (defun *error* ( msg )
    (if oldOsmode  (setvar "OSMODE"  oldOsmode))
    (if oldDynmode (setvar "DYNMODE" oldDynmode))
    (if oldCmdecho (setvar "CMDECHO" oldCmdecho))
    (if oldClayer  (setvar "CLAYER"  oldClayer))
    (if (and msg (not (wcmatch (strcase msg) "*CANCEL*,*ABORT*,*EXIT*")))
      (princ (strcat "\nVirhe: " msg)))
    (princ)
  )

  (vl-load-com)

  (setq oldClayer  (getvar "CLAYER"))
  (setq oldCmdecho (getvar "CMDECHO"))
  (setq oldOsmode  (getvar "OSMODE"))
  (setq oldDynmode (getvar "DYNMODE"))

  (setvar "CMDECHO" 0)
  ;; Dynamic input paalle valinnan ajaksi: keyword-lista naytetaan kursorin
  ;; vieressa nuolinappaimin selattavana (toimii seka AutoCAD etta BricsCAD).
  (setvar "DYNMODE" 3)

  ;; 1) Valitse laite. Keyword-lyhennteet uniikit: A/S/P/R/K/H.
  (initget "Anturi Sireeni Pc Ryhmakeskus Keskus Hataseis")
  (setq choice
    (getkword
      (strcat
        "\nValitse varuste "
        "[Anturi/Sireeni/Pc/Ryhmakeskus/Keskus/Hataseis] "
        "<Anturi>: ")))
  (if (null choice) (setq choice "Anturi"))

  ;; 2) Hae mappaus-rivi
  (setq entry (assoc choice varusteet-device-map))
  (if (null entry)
    (progn
      (princ (strcat "\nVirhe: tuntematon varuste '" choice "'"))
      (setvar "DYNMODE" oldDynmode)
      (setvar "CMDECHO" oldCmdecho)
      (setvar "CLAYER"  oldClayer)
      (exit)))
  (setq dwgName    (nth 1 entry))
  (setq blockName  (nth 2 entry))
  (setq layerName  (nth 3 entry))
  (setq colorIndex (nth 4 entry))

  ;; 3) Block-maaritys: lataa ensikerralla DWG:sta block-tauluun.
  ;;    -INSERT name=path ajetaan VAIN kerran, kontrolloidusti origoon
  ;;    ja poistetaan heti. Varsinainen sijoitus tehdaan vla-InsertBlock:lla
  ;;    (sama strategia kuin klhylly.lsp) — ei riipu -INSERT:n prompt-
  ;;    sekvenssista, joka eroaa AutoCADin ja BricsCADin valilla ja
  ;;    aiheutti vaaran blockin / scalen BricsCADissa.
  (setq firstTime (not (tblsearch "BLOCK" blockName)))
  (if firstTime
    (progn
      (setq blockPath (varusteet-find-block-file dwgName))
      (if (null blockPath)
        (progn
          (princ (strcat
            "\nVIRHE: " dwgName " ei loydy. Varmista etta tiedosto on samassa"
            "\nkansiossa kuin varusteet.lsp. (DWG-tiedostot kuuluvat"
            "\nsuunnittelutyokalut.zip-pakettiin.)"))
          (setvar "DYNMODE" oldDynmode)
          (setvar "CMDECHO" oldCmdecho)
          (setvar "CLAYER"  oldClayer)
          (exit)))
      (setq savedFiledia (getvar "FILEDIA"))
      (setq savedCmddia  (getvar "CMDDIA"))
      (setq savedExpert  (getvar "EXPERT"))
      (setvar "FILEDIA" 0)
      (setvar "CMDDIA"  0)
      (setvar "EXPERT"  5)
      (vl-catch-all-apply
        '(lambda ()
           (command "_.-INSERT" (strcat blockName "=" blockPath) "0,0,0" 1 1 0)
           (if (entlast) (entdel (entlast)))))
      (setvar "FILEDIA" savedFiledia)
      (setvar "CMDDIA"  savedCmddia)
      (setvar "EXPERT"  savedExpert)
    )
  )

  ;; 4) Varmista target-layer + aseta CLAYER:ksi jotta uusi instanssi
  ;;    menee oikealle layerille.
  (varusteet-ensure-layer layerName colorIndex)
  (setvar "CLAYER" layerName)

  ;; 5) Insertoi block interaktiivisesti -INSERT:lla. Block on jo
  ;;    block-taulussa (vaihe 3), joten "-INSERT blockName" nayttaa
  ;;    drag-preview:n kun kayttaja etsii sijoituspaikkaa.
  ;;    "_S" 1 lukitsee skaalan 1:ksi heti (Scale-keyword insertion-
  ;;    point-promptissa) - nain skaalaa EI kysyta erikseen. while-pause
  ;;    -loop luovuttaa loput (insertointipiste + rotaatio) kayttajalle.
  ;;    Toimii seka AutoCAD etta BricsCAD vaikka niiden -INSERT-prompt-
  ;;    sekvenssi muuten eroaa.
  (command "_.-INSERT" blockName "_S" 1)
  (while (= 1 (logand 1 (getvar "CMDACTIVE")))
    (command pause))

  ;; 6) Palauta tila
  (setvar "OSMODE"  oldOsmode)
  (setvar "DYNMODE" oldDynmode)
  (setvar "CMDECHO" oldCmdecho)
  (setvar "CLAYER"  oldClayer)
  (princ)
)

(princ "\nVARUSTEET.LSP ladattu - komento: VARUSTEET")
(princ)
