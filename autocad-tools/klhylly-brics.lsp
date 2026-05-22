;;; KLHYLLY-BRICS.LSP - Kylmalaitehyllyn piirtokomennot (BricsCAD-versio)
;;;
;;; CAD-SPESIFI: tama on BricsCAD-versio. Dynamic-block-parametrit
;;; asetetaan jarjestyksessa Leveys -> Pituus, ja Layer+Properties:n
;;; jalkeen ajetaan REGEN. BricsCAD ei ketjuta Leveys-Stretch +
;;; Pituus-Array -yhdistelmaa jalkikateen eika evaluoi dynamic-block-
;;; actioneita reaaliaikaisesti, joten leveys on asetettava ennen kuin
;;; pituus laukaisee arrayn ja REGEN pakottaa lopullisen evaluoinnin.
;;; AutoCAD-versio on klhylly.lsp (Pituus-ensin, ei REGEN-pakkoa).
;;; Asentajan generoima acaddoc.lsp valitsee oikean per (getvar "PRODUCT").
;;;
;;; Riippuvuus: rinnalla files/klhylly-levy-brics.dwg ja
;;;             files/klhylly-tikas-brics.dwg (BricsCAD-tallennetut
;;;             dynamic-block-kirjastot — AutoCAD-versiot ovat ilman
;;;             -brics-paatetta klhylly.lsp:n kaytossa)
;;; -block-kirjastot, jotka sisaltavat dynamic blockit KLHYLLY-LEVY ja
;;; KLHYLLY-TIKAS. Blockit on parametrisoitu: Pituus (Linear, continuous)
;;; ja Leveys (Linear, List 300/400/500), molemmat muokattavissa
;;; Properties-paletissa. Pituutta voi myos stretchata gripeilla; TIKAS:n
;;; rungit lisataan/poistetaan automaattisesti 250 mm askeleella array-
;;; actionin myota.
;;;
;;; Erilliset DWG:t per blocki valttaa AutoCAD:n self-reference-virheet
;;; jotka voivat syntya kun molemmat blockit ovat samassa lahde-DWG:ssa.
;;;
;;; Lataa: APPLOAD -> valitse tama tiedosto. (klhylly-levy.dwg ja
;;; klhylly-tikas.dwg loydetaan automaattisesti samasta kansiosta.)
;;;
;;; Komennot:
;;;   KLH   -> LEVY/TIKAS -> 300/400/500 -> V=vasen / K=keski -> pisteet
;;;   KLHL  -> piirra LEVY-hylly suoraan (ribbon, ei tyyppipromptia)
;;;   KLHT  -> piirra TIKAS-hylly suoraan (ribbon, ei tyyppipromptia)
;;;   KLHV  -> 300/400/500 -> alkupiste -> loppupiste (pick tai Z=pystysuunta) -> rotaatio
;;;   KORKO      -> valitse kohteet -> kohdekorko z mm
;;;
;;; Layerit luodaan automaattisesti: KYL-LEVYHYLLY ja KYL-TIKASHYLLY,
;;; molemmat AutoCAD Color Index 175 (RGB 63,63,127). Block-maaritysten sisalla geometria
;;; on layerilla 0 (BYBLOCK), joten instanssin layer periytyy alaspain
;;; ja IFC-vienti (dxf2ifc) tunnistaa hyllytyypin.
;;;
;;; KLH-syotto: pick start (p1) -> pick end (p2). Pituus = distance(p1,p2).
;;; Aloituspisteen sijainti hyllyssa valitaan V/K-promptilla:
;;;   V (vasen paa) = kursori on hyllyn vasemmassa ALAKULMASSA. INSERT = p1.
;;;                   Alkuperainen TIKAS-pick-start-kaytos.
;;;   K (keski)     = kursori on hyllyn vasemmassa paassa LEVEYDEN keskella.
;;;                   INSERT = p1 siirretty Leveys/2 perp:n vastakkaiseen
;;;                   suuntaan -> alareuna menee Leveys/2 alapuolelle ja
;;;                   ylareuna Leveys/2 ylapuolelle. Toimii kummallakin
;;;                   scaleY-arvolla koska +Y_local maailmassa = perp.
;;; Edellinen valinta muistetaan session ajan (klhylly-last-startmode).
;;; Snap-corner-fallback (<= 80 mm KYL-*HYLLY-nurkkaan) on molemmille
;;; pisteille kummassakin moodissa. Auto-perp valitsee leveyssuunnan
;;; testaten p1:sta. CW-puolella scaleY=-1 (peilaus).

(vl-load-com)

;; ============================================================
;; LAYER + SNAP HELPERIT
;; ============================================================

;; Varmistaa etta layer on olemassa annetulla AutoCAD color index:lla.
;; Jos layer on jo olemassa, ei kosketa sen asetuksiin (kayttajan custom-vari sailyy).
(defun klhylly-ensure-layer ( layerName colorIndex
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

(defun klhylly-point-occupied-p ( pt / delta ss )
  (setq delta 0.5)
  (setq ss (ssget "_C"
                   (list (- (car pt) delta) (- (cadr pt) delta))
                   (list (+ (car pt) delta) (+ (cadr pt) delta))
                   '((8 . "KYL-*HYLLY"))))
  (not (null ss))
)

(defun klhylly-solid-bbox-corners ( ent / obj minArr maxArr result mn mx )
  (setq obj (vlax-ename->vla-object ent))
  (setq minArr nil maxArr nil)
  (setq result
    (vl-catch-all-apply 'vla-GetBoundingBox (list obj 'minArr 'maxArr)))
  (if (and (not (vl-catch-all-error-p result)) minArr maxArr)
    (progn
      (setq mn (vlax-safearray->list minArr))
      (setq mx (vlax-safearray->list maxArr))
      (list
        (list (nth 0 mn) (nth 1 mn))
        (list (nth 0 mx) (nth 1 mn))
        (list (nth 0 mx) (nth 1 mx))
        (list (nth 0 mn) (nth 1 mx))
      )
    )
    nil
  )
)

;; Etsii lahimman nurkan KYL-*HYLLY-entiteetista p1:sta. Toimii sekä
;; vanhoille (LWPOLYLINE/3DSOLID) etta uusille (INSERT block) hyllyille.
(defun klhylly-snap-corner ( pt / boxR maxDist ss i ent entType corners
                                   best bestD c d )
  (setq boxR 100.0)
  (setq maxDist 80.0)
  (setq ss (ssget "_C"
                   (list (- (car pt) boxR) (- (cadr pt) boxR))
                   (list (+ (car pt) boxR) (+ (cadr pt) boxR))
                   '((8 . "KYL-*HYLLY"))))
  (setq best nil bestD maxDist)
  (if ss
    (progn
      (setq i 0)
      (while (< i (sslength ss))
        (setq ent     (ssname ss i))
        (setq entType (cdr (assoc 0 (entget ent))))
        (setq corners
          (cond
            ((= entType "LWPOLYLINE")
              (mapcar '(lambda (pr)
                          (list (car (cdr pr)) (cadr (cdr pr))))
                      (vl-remove-if-not '(lambda (pr) (= (car pr) 10))
                                        (entget ent))))
            ((= entType "3DSOLID")
              (klhylly-solid-bbox-corners ent))
            ((= entType "INSERT")
              (klhylly-solid-bbox-corners ent))
            (t nil)
          )
        )
        (foreach c corners
          (setq d (distance (list (car pt) (cadr pt))
                            (list (car c) (cadr c))))
          (if (< d bestD)
            (progn
              (setq best  (list (car c) (cadr c) 0.0))
              (setq bestD d)
            )
          )
        )
        (setq i (1+ i))
      )
    )
  )
  best
)

(defun klhylly-auto-perp ( p1 ang / perpCCW perpCW occCCW occCW d )
  (setq perpCCW (+ ang (/ pi 2.0)))
  (setq perpCW  (- ang (/ pi 2.0)))
  (setq occCCW nil occCW nil)
  (foreach d '(5.0 50.0)
    (if (null occCCW)
      (if (klhylly-point-occupied-p (polar p1 perpCCW d))
        (setq occCCW T)))
    (if (null occCW)
      (if (klhylly-point-occupied-p (polar p1 perpCW d))
        (setq occCW T)))
  )
  (cond
    ((and occCCW (not occCW)) perpCCW)
    ((and (not occCCW) occCW) perpCW)
    (t perpCCW)
  )
)

;; ============================================================
;; BLOCK-DWG LOCATOR (kuvio kopioitu positio.lsp:sta)
;; ============================================================

(defun klhylly-self-folder ( / found regbase target ver prod prof appkey val )
  (vl-load-com)
  (setq target "klhylly.lsp")
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

;; Etsii block-DWG:n nimella (klhylly-levy.dwg tai klhylly-tikas.dwg).
;; Erilliset DWG:t valttavat self-reference-virheet jotka tulevat kun
;; molemmat blockit ovat samassa lahde-DWG:ssa.
;; Hakujarjestys: ENSIN klhylly-brics.lsp:n oma kansio (DWG matkaa
;; LSP:n rinnalla — ZIP, asennus, repo), sitten vakioasennus. Paljas
;; findfile on demotettu viimeiseksi: se etsii myos avoimen piirustuksen
;; kansiosta, ja samanniminen hajatiedosto kaataisi -INSERTin
;; "block references itself" -virheeseen.
(defun klhylly-find-block-file ( dwgName / cands self found p )
  (vl-load-com)
  (setq cands '())
  ;; 1. klhylly-brics.lsp:n oma kansio.
  (if (setq self (klhylly-self-folder))
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
;; DYNAMIC BLOCK PROPERTY -SETTERI
;; ============================================================

;; Asettaa dynamic blockin parametrin arvon nimella. Hiljaa epaonnistuu
;; jos parametria ei ole tai arvo ei kuulu sallittuihin (List-tyyppinen).
(defun klhylly-set-dyn-prop ( ent propName value / obj props p )
  (setq obj (vlax-ename->vla-object ent))
  (setq props (vlax-invoke obj 'GetDynamicBlockProperties))
  (foreach p props
    (if (= (strcase (vla-get-PropertyName p)) (strcase propName))
      (vla-put-Value p (vlax-make-variant value vlax-vbDouble))
    )
  )
)

;; ============================================================
;; KLH-PIIRTOAPURI — jaettu c:KLH / c:KLHL / c:KLHT kesken
;; ============================================================
;; tyyppi    = "LEVY" tai "TIKAS"
;; levy      = leveys mm (300 / 400 / 500)
;; startMode = "V" (vasen paa) tai "K" (keski)
;; Ei prompteja tyypille/leveydelle — kutsuja on jo paattanyt ne.
;; Siirtyy suoraan pisteiden valintaan (vaakahylly).

(defun klhylly-draw-h ( tyyppi levy startMode
                     / *error* oldClayer oldCmdecho oldOsmode
                       p1 p1snap p2 pituus ang perp insertPt
                       blockName dwgName blockPath layerName scaleY firstTime
                       doc ms ins
                       savedFiledia savedCmddia savedExpert )

  (defun *error* ( msg )
    (if oldOsmode  (setvar "OSMODE"  oldOsmode))
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

  (setvar "CMDECHO" 0)

  ;; CAD-spesifit DWG:t: BricsCAD-versio kayttaa -brics-block-kirjastoja
  ;; jotka on tallennettu BricsCAD:lla. AutoCAD-versio (klhylly.lsp)
  ;; kayttaa klhylly-levy.dwg / klhylly-tikas.dwg.
  (cond
    ((= tyyppi "TIKAS")
      (setq blockName "KLHYLLY-TIKAS")
      (setq dwgName   "klhylly-tikas-brics.dwg")
      (setq layerName "KYL-TIKASHYLLY"))
    (t
      (setq blockName "KLHYLLY-LEVY")
      (setq dwgName   "klhylly-levy-brics.dwg")
      (setq layerName "KYL-LEVYHYLLY"))
  )

  ;; 3) Block-maaritys: ensikerralla lookup vastaavan DWG:n polku
  (setq firstTime (not (tblsearch "BLOCK" blockName)))
  (if firstTime
    (progn
      (setq blockPath (klhylly-find-block-file dwgName))
      (if (null blockPath)
        (progn
          (princ (strcat "\nVIRHE: " dwgName " ei loydy. Varmista etta tiedosto on samassa"))
          (princ "\nkansiossa kuin klhylly.lsp.")
          (setvar "CMDECHO" oldCmdecho)
          (setvar "CLAYER"  oldClayer)
          (exit)
        )
      )
    )
  )

  ;; 4) Pisteet — sama pick-start -> pick-end molemmissa moodeissa.
  ;;    V/K eroavat vain INSERT-pisteen Y-laskennassa (alla).
  (setvar "OSMODE" (logior (logand oldOsmode 16383) 33))
  (setq p1 (getpoint "\nPick start point: "))
  (setvar "OSMODE" oldOsmode)
  (if (null p1) (exit))
  (setq p1 (list (car p1) (cadr p1) 0.0))
  (setq p1snap (klhylly-snap-corner p1))
  (if p1snap (setq p1 p1snap))

  (setvar "OSMODE" (logior (logand oldOsmode 16383) 33))
  (setq p2 (getpoint p1 "\nPick length end point: "))
  (setvar "OSMODE" oldOsmode)
  (if (null p2) (exit))
  (setq p2 (list (car p2) (cadr p2) 0.0))
  (setq pituus (distance p1 p2))
  (if (<= pituus 0.0) (exit))
  (setq ang  (angle p1 p2))
  (setq perp (klhylly-auto-perp p1 ang))

  ;; INSERT-piste: V = p1 (kursori vasemmassa alakulmassa, alkuperainen),
  ;;               K = p1 + Leveys/2 perp:n vastakkaiseen suuntaan
  ;;                   (kursori Y-keskella, hylly Y-leviaa molempiin puoliin).
  (setq insertPt
    (if (= startMode "K")
      (polar p1 (+ perp pi) (* 0.5 levy))
      p1))

  ;; 5) scaleY (CW = peilaa Y -> width kasvaa toiselle puolelle)
  (setq scaleY
    (if (equal perp (+ ang (/ pi 2.0)) 0.0001)
      1.0
      -1.0
    )
  )

  ;; 7) Layer luonti tarvittaessa
  (klhylly-ensure-layer layerName 175)

  ;; 8) Lataa block-maaritys ensikerralla -INSERT:lla origin:iin ja poista
  ;;    valittomasti. FILEDIA/CMDDIA/EXPERT vaihdetaan vain talle kapealle
  ;;    blokille jotta -INSERT ei avaa file dialogia, ja palautetaan heti
  ;;    perään. vl-catch-all-apply takaa palautuksen vaikka -INSERT epaonnistuisi.
  (if firstTime
    (progn
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

  ;; 9) Sijoita instanssi vla-InsertBlock:lla — rotation radiaaneina,
  ;;     scaleY = -1.0 mirroria varten kun perp on CW. Ei prompteja.
  (setq doc (vla-get-ActiveDocument (vlax-get-acad-object)))
  (setq ms  (vla-get-ModelSpace doc))
  (setq ins (vla-InsertBlock ms (vlax-3d-point insertPt) blockName 1.0 scaleY 1.0 ang))

  ;; 10) Aseta layer + dynaamiset properties.
  ;;     JARJESTYS: Leveys ENNEN Pituutta. KLHYLLY-TIKAS:n Leveys-Stretch
  ;;     venyttaa rung-masteria; Pituus-Array kopioi sen. BricsCAD ei
  ;;     ketjuta Stretch+Array-yhdistelmaa jalkikateen, joten leveys on
  ;;     asetettava ennen kuin pituus laukaisee arrayn — nain array
  ;;     kopioi jo-venytetyn masterin. AutoCAD evaluoi koko blockin
  ;;     lopuksi, joten jarjestyksella ei ole sille merkitysta.
  (vla-put-Layer ins layerName)
  (klhylly-set-dyn-prop (vlax-vla-object->ename ins) "Leveys" levy)
  (klhylly-set-dyn-prop (vlax-vla-object->ename ins) "Pituus" pituus)
  ;; BricsCAD ei evaluoi dynamic-block-actioneita (Stretch/Array)
  ;; reaaliaikaisesti parametrin muutoksen jalkeen — REGEN pakottaa
  ;; evaluoinnin niin etta rungit/leveys nakyvat heti oikein. AutoCAD
  ;; hyvaksyy saman REGEN:n harmittomasti.
  (vl-catch-all-apply '(lambda () (command "_.REGEN")))

  (setvar "OSMODE"  oldOsmode)
  (setvar "CMDECHO" oldCmdecho)
  (setvar "CLAYER"  oldClayer)

  (princ "\nHylly valmis. Properties-paletista voi vaihtaa Leveys/Pituus.")
  (princ)
)

;; ============================================================
;; KLH / KLHL / KLHT — kayttajakomennot
;; ============================================================
;; KLH  = komentorivi: kysyy tyypin, leveyden ja aloituspisteen.
;; KLHL = piirra LEVY-hylly suoraan (ribbon). Ei tyyppipromptia.
;; KLHT = piirra TIKAS-hylly suoraan (ribbon). Ei tyyppipromptia.
;; KLHL/KLHT kayttavat valikon viimeisinta leveytta (KLH-W*) ja
;; aloituspistetta (KLH-SNAP*); oletus 300 mm / V.

(defun c:KLH ( / *error* tyyppi levyStr startMode )

  (defun *error* ( msg )
    (if (and msg (not (wcmatch (strcase msg) "*CANCEL*,*ABORT*,*EXIT*")))
      (princ (strcat "\nVirhe: " msg)))
    (princ)
  )

  ;; 1) Tyyppi — oletus globaalista klhylly-last-tyyppi.
  (if (null klhylly-last-tyyppi) (setq klhylly-last-tyyppi "LEVY"))
  (initget "LEVY TIKAS")
  (setq tyyppi (getkword (strcat "\nSelect type [LEVY/TIKAS] <"
                                  klhylly-last-tyyppi ">: ")))
  (if (null tyyppi) (setq tyyppi klhylly-last-tyyppi))
  (setq klhylly-last-tyyppi tyyppi)

  ;; 2) Leveys — oletus globaalista klhylly-last-levy.
  (if (null klhylly-last-levy) (setq klhylly-last-levy "300"))
  (initget "300 400 500")
  (setq levyStr (getkword (strcat "\nSelect plate [300/400/500] <"
                                   klhylly-last-levy ">: ")))
  (if (null levyStr) (setq levyStr klhylly-last-levy))
  (setq klhylly-last-levy levyStr)

  ;; 2b) Aloituspiste — V = hyllyn vasen paa, K = hyllyn keski.
  (if (null klhylly-last-startmode) (setq klhylly-last-startmode "V"))
  (initget "V K")
  (setq startMode (getkword (strcat "\nAloituspiste [V=vasen paa / K=keski] <"
                                     klhylly-last-startmode ">: ")))
  (if (null startMode) (setq startMode klhylly-last-startmode))
  (setq klhylly-last-startmode startMode)

  (klhylly-draw-h tyyppi (atof levyStr) startMode)
  (princ)
)

;; Ribbon-piirtokomennot: nappi paattaa tyypin, ei tyyppipromptia.
(defun c:KLHL ( / )
  (setq klhylly-last-tyyppi "LEVY")
  (if (null klhylly-last-levy)      (setq klhylly-last-levy "300"))
  (if (null klhylly-last-startmode) (setq klhylly-last-startmode "V"))
  (klhylly-draw-h "LEVY" (atof klhylly-last-levy) klhylly-last-startmode)
  (princ)
)
(defun c:KLHT ( / )
  (setq klhylly-last-tyyppi "TIKAS")
  (if (null klhylly-last-levy)      (setq klhylly-last-levy "300"))
  (if (null klhylly-last-startmode) (setq klhylly-last-startmode "V"))
  (klhylly-draw-h "TIKAS" (atof klhylly-last-levy) klhylly-last-startmode)
  (princ)
)

;; ============================================================
;; KLHV (TIKAS-hylly kahden pisteen valiin, vapaa 3D-suunta)
;; ============================================================
;; Sama dynamic block KLHYLLY-TIKAS kuin vaakaversiossa. Sama
;; toimintaperiaate kuin kotelo.lsp:ssa: pick alkupiste -> loppupiste
;; (pick tai keyword Z = kirjoita +/- Z-pituus, esim. -2100 = pystyhylly
;; 2100 mm alaspain) -> rotaatio tavallisella ROTATE:lla (live-preview).
;; Pituussuunta tulee pisteista, korkeus = maailman +Z kohtisuoraksi
;; tehtyna L:aa vasten (lahes pystysuoralla hyllylla fallback +X),
;; leveys vaakaan kohtisuoraan. INSERT WCS-origoon + vla-TransformBy.

(defun c:KLHV ( / *error* oldClayer oldCmdecho oldOsmode
                     blockName dwgName blockPath layerName firstTime
                     levyStr levy
                     p1 inp dz p2 length
                     Lraw Lmag L Zw dotZL Draw Dmag D Xw dotXL W
                     minPt maxPt bbRes bbMin bbMax halfW halfH
                     anchorY anchorZ
                     mat doc ms ins ename
                     savedFiledia savedCmddia savedExpert )

  (defun *error* ( msg )
    (if oldOsmode    (setvar "OSMODE"  oldOsmode))
    (if oldCmdecho   (setvar "CMDECHO" oldCmdecho))
    (if oldClayer    (setvar "CLAYER"  oldClayer))
    ;; firstTime-haaran sysvar-tallennukset — palautetaan vain jos
    ;; ehdittiin tallentaa (muuten nil, ei kosketa).
    (if savedFiledia (setvar "FILEDIA" savedFiledia))
    (if savedCmddia  (setvar "CMDDIA"  savedCmddia))
    (if savedExpert  (setvar "EXPERT"  savedExpert))
    (if (and msg (not (wcmatch (strcase msg) "*CANCEL*,*ABORT*,*EXIT*")))
      (princ (strcat "\nVirhe: " msg)))
    (princ)
  )

  (vl-load-com)

  (setq oldClayer  (getvar "CLAYER"))
  (setq oldCmdecho (getvar "CMDECHO"))
  (setq oldOsmode  (getvar "OSMODE"))

  (setvar "CMDECHO" 0)

  (setq blockName "KLHYLLY-TIKAS")
  (setq dwgName   "klhylly-tikas-brics.dwg")   ; BricsCAD-spesifi block-kirjasto
  (setq layerName "KYL-TIKASHYLLY")

  ;; 1) Leveys — jaettu globaali klhylly-last-levy KLH:n kanssa.
  (if (null klhylly-last-levy) (setq klhylly-last-levy "300"))
  (initget "300 400 500")
  (setq levyStr (getkword (strcat "\nLeveys [300/400/500] <"
                                   klhylly-last-levy ">: ")))
  (if (null levyStr) (setq levyStr klhylly-last-levy))
  (setq klhylly-last-levy levyStr)
  (setq levy (atof levyStr))

  ;; 2) Block-maaritys
  (setq firstTime (not (tblsearch "BLOCK" blockName)))
  (if firstTime
    (progn
      (setq blockPath (klhylly-find-block-file dwgName))
      (if (null blockPath)
        (progn (princ (strcat "\nVIRHE: " dwgName " ei loydy.")) (exit))
      )
    )
  )

  ;; 3) Alkupiste + loppupiste. Loppupiste: klikkaa piste, TAI kirjoita
  ;;    +/- pituus Z-suunnassa (pystyhylly, esim. -2100 = 2100 mm alas).
  ;;    initget 128 nappaa kirjoitetun luvun stringina; keyword Z on
  ;;    varmempi reitti samaan. Base pointia EI anneta getpointille —
  ;;    muuten kirjoitettu luku menisi direct distance entry:lle ja
  ;;    tekisi vaakahyllyn vaaraan suuntaan.
  (setq p1 (getpoint "\nHyllyn alkupiste: "))
  (if (null p1) (exit))
  (initget 128 "Z")
  (setq inp (getpoint "\nHyllyn loppupiste, +/- Z-pituus, tai [Z]: "))
  (cond
    ((null inp) (exit))
    ((equal inp "Z")
      (setq dz (getreal "\nPituus Z-suunnassa (+ = ylos / - = alas): "))
      (if (or (null dz) (< (abs dz) 1.0))
        (progn (princ "\nLiian pieni pituus.") (exit)))
      (setq p2 (list (car p1) (cadr p1) (+ (caddr p1) dz))))
    ((eq (type inp) 'STR)
      (setq dz (atof inp))
      (if (< (abs dz) 1.0)
        (progn (princ "\nVirheellinen syote.") (exit)))
      (setq p2 (list (car p1) (cadr p1) (+ (caddr p1) dz))))
    (t (setq p2 inp))
  )

  ;; 4) Pituusakseli L = yksikkovektori p1->p2
  (setq Lraw (mapcar '- p2 p1))
  (setq Lmag (distance '(0.0 0.0 0.0) Lraw))
  (if (< Lmag 1.0)
    (progn (princ "\nPituus liian lyhyt.") (exit)))
  (setq length Lmag)
  (setq L (list (/ (car Lraw)   Lmag)
                (/ (cadr Lraw)  Lmag)
                (/ (caddr Lraw) Lmag)))

  ;; 5) Korkeusakseli D = maailman +Z kohtisuoraksi tehtyna L:aa vasten.
  ;;    Lahes pystysuoralla hyllylla fallback maailman +X:aan.
  (setq Zw '(0.0 0.0 1.0))
  (setq dotZL (caddr L))
  (setq Draw (mapcar '- Zw (list (* dotZL (car L))
                                 (* dotZL (cadr L))
                                 (* dotZL (caddr L)))))
  (setq Dmag (distance '(0.0 0.0 0.0) Draw))
  (if (< Dmag 0.001)
    (progn
      (setq Xw '(1.0 0.0 0.0))
      (setq dotXL (car L))
      (setq Draw (mapcar '- Xw (list (* dotXL (car L))
                                     (* dotXL (cadr L))
                                     (* dotXL (caddr L)))))
      (setq Dmag (distance '(0.0 0.0 0.0) Draw))
    )
  )
  (setq D (list (/ (car Draw)   Dmag)
                (/ (cadr Draw)  Dmag)
                (/ (caddr Draw) Dmag)))

  ;; 6) Leveysakseli W = D x L (oikeakatinen kanta: L x W = D)
  (setq W (list
            (- (* (cadr D)  (caddr L)) (* (caddr D) (cadr L)))
            (- (* (caddr D) (car L))   (* (car D)   (caddr L)))
            (- (* (car D)   (cadr L))  (* (cadr D)  (car L)))))

  ;; 7) Layer luonti
  (klhylly-ensure-layer layerName 175)

  ;; 8) Lataa block-maaritys ensikerralla -INSERT:lla origin:iin ja poista
  ;;    valittomasti. FILEDIA/CMDDIA/EXPERT vain talle kapealle blokille.
  (if firstTime
    (progn
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

  ;; 9) Sijoita instanssi WCS-origoon vla-InsertBlock:lla
  (setq doc (vla-get-ActiveDocument (vlax-get-acad-object)))
  (setq ms  (vla-get-ModelSpace doc))
  (setq ins (vla-InsertBlock ms (vlax-3d-point '(0.0 0.0 0.0))
                             blockName 1.0 1.0 1.0 0.0))

  ;; 9b) Anchor auto-detect orientaation mukaan — SAMA LOGIIKKA KUIN
  ;;     KOTELO:SSA. Aiempi yritys (halfH=17.5 = tikkaiden keski) embed-asi
  ;;     vaakaan koska anchor oli cross-sectionin sisalla.
  ;;
  ;;     halfW = levy/2 (kayttaja valitsi 300/400/500).
  ;;     halfH = bboxin Z-extent/2 (rail-korkeus / 2, default 30 mm).
  ;;     anchorY = halfW (aina lateral keski).
  ;;     anchorZ:
  ;;       - VAAKA (null dz, pickattu loppupiste): 0 (rail-pohja)
  ;;         -> TIKAS lepaa pinnalla, ei upota
  ;;       - PYSTYPUDOTUS (dz < 0): 2*halfH = rail-yläpinta
  ;;         -> TIKAS riippuu pinnan alapuolelta, ei upota kattoon
  ;;       - PYSTYNOUSU (dz > 0): 0 (rail-pohja)
  (setq halfW (* 0.5 levy))
  (setq halfH 30.0)
  (setq minPt nil  maxPt nil)
  (setq bbRes (vl-catch-all-apply
                'vla-GetBoundingBox (list ins 'minPt 'maxPt)))
  (if (and (not (vl-catch-all-error-p bbRes)) minPt maxPt)
    (progn
      (setq bbMin (vlax-safearray->list minPt))
      (setq bbMax (vlax-safearray->list maxPt))
      (setq halfH (* 0.5 (- (caddr bbMax) (caddr bbMin))))
    )
  )
  (setq anchorY halfW)
  (setq anchorZ
    (cond
      ((null dz) 0.0)                  ; vaaka -> rail-pohja
      ((< dz 0)  (* 2.0 halfH))        ; pudotus -> rail-yläpinta
      (t         0.0)))                ; nousu -> rail-pohja

  ;; 10) 4x4-muunnos: kanonisen X -> L, Y -> W, Z -> D.
  ;;     Translaatio = p1 - anchorY*W - anchorZ*D, jotta block-koord
  ;;     (0, anchorY, anchorZ) landaa pickattuun pisteeseen p1.
  (setq mat
    (vlax-tmatrix
      (list
        (list (car L)   (car W)   (car D)
              (- (car p1)   (* anchorY (car W))   (* anchorZ (car D))))
        (list (cadr L)  (cadr W)  (cadr D)
              (- (cadr p1)  (* anchorY (cadr W))  (* anchorZ (cadr D))))
        (list (caddr L) (caddr W) (caddr D)
              (- (caddr p1) (* anchorY (caddr W)) (* anchorZ (caddr D))))
        (list 0.0 0.0 0.0 1.0))))
  (vla-TransformBy ins mat)

  ;; 11) Layer + dynaamiset properties. Leveys ENNEN Pituutta — ks. c:KLH
  ;;     vaihe 10: BricsCAD ei ketjuta Leveys-Stretch + Pituus-Array.
  (vla-put-Layer ins layerName)
  (klhylly-set-dyn-prop (vlax-vla-object->ename ins) "Leveys" levy)
  (klhylly-set-dyn-prop (vlax-vla-object->ename ins) "Pituus" length)
  ;; REGEN pakottaa BricsCADin evaluoimaan dynamic-block-actionit — ks. c:KLH.
  (vl-catch-all-apply '(lambda () (command "_.REGEN")))

  ;; 12) Rotaatio: tavallinen 2D-ROTATE p1:n ympari. AutoCAD nayttaa
  ;;     natiivin dynaamisen previewn kun kayttaja liikuttaa hiirta —
  ;;     voi myos kirjoittaa kulman. Esc/Enter = ei kiertoa.
  (setq ename (vlax-vla-object->ename ins))
  (vl-catch-all-apply
    '(lambda ()
       (command "_.ROTATE" ename "" (trans p1 0 1) pause)))

  (setvar "OSMODE"  oldOsmode)
  (setvar "CMDECHO" oldCmdecho)
  (setvar "CLAYER"  oldClayer)

  (princ "\nKLHV valmis.")
  (princ)
)

;; ============================================================
;; KORKO - siirtaa valitut kohteet absoluuttiselle Z-korolle
;; ============================================================
;; Toimii kaikille entiteeteille: INSERT-blokit (hyllyt, hoyrystimet,
;; koneikot, kompressorit) ja vanhat UNION-3DSOLIDit (MOVE-pohjainen).
;;
;; Referenssi-Z per entiteetti:
;;   INSERT  -> insertion pointin Z (sama kuin AutoCAD Properties nayttaa)
;;   muut    -> vla-GetBoundingBox bbox-min Z (3DSOLID/REGION/POLYLINE)
;;
;; Useita kohteita kerralla: alin referenssi-Z siirtyy annettuun
;; kohdekorkoon, muut shiftaavat saman delta:n verran -> suhteelliset
;; Z-erot sailyvat.

(defun klhylly-ref-z ( ent / d obj minArr maxArr res )
  ;; Palauta entiteetin referenssi-Z (INSERT -> group 10 Z,
  ;; muut -> vla-GetBoundingBox alareuna). nil jos ei saatavilla.
  (setq d (entget ent))
  (if (eq (cdr (assoc 0 d)) "INSERT")
    (caddr (cdr (assoc 10 d)))
    (progn
      (setq obj (vlax-ename->vla-object ent))
      (setq minArr nil maxArr nil)
      (setq res
        (vl-catch-all-apply 'vla-GetBoundingBox (list obj 'minArr 'maxArr)))
      (if (and (not (vl-catch-all-error-p res)) minArr)
        (nth 2 (vlax-safearray->list minArr))
        nil))))

(defun c:KORKO ( / ss i ent refZ curZ targetZ delta )

  (prompt "\nValitse kohteet: ")
  (setq ss (ssget))

  (if (null ss)
    (progn
      (princ "\nEi valittuja kohteita.")
      (princ)
    )
    (progn
      (setq i 0 curZ nil)
      (while (< i (sslength ss))
        (setq ent (ssname ss i))
        (setq refZ (klhylly-ref-z ent))
        (if refZ
          (if (or (null curZ) (< refZ curZ))
            (setq curZ refZ)))
        (setq i (1+ i))
      )
      (if (null curZ) (setq curZ 0.0))

      (princ (strcat "\nNykyinen Z (alin): " (rtos curZ 2 1) " mm"))
      (setq targetZ (getreal "\nKohdekorko (Z mm): "))

      (if (null targetZ)
        (princ "\nKeskeytetty.")
        (progn
          (setq delta (- targetZ curZ))
          (command "_.MOVE" ss "" '(0.0 0.0 0.0) (list 0.0 0.0 delta))
          (princ
            (strcat "\nSiirretty " (rtos delta 2 1) " mm -> Z = "
                    (rtos targetZ 2 1)))
        )
      )
    )
  )
  (princ)
)

;; ============================================================
;; RIBBON-VALIKON SETTER-KOMENNOT
;; ============================================================
;; Naita kutsutaan Hyllyt-paneelin leveys/snap-dropdowneista.
;; Ne vain asettavat globaalin oletuksen — eivat piirra mitaan.
;; Ribbonin Levyhylly/Tikashylly-painikkeet ajavat KLHL/KLHT jotka
;; lukevat nama oletukset ja siirtyvat suoraan pisteiden valintaan.
;; KLH-LEVY/KLH-TIKAS jaavat varalle (komentorivi / vanhat makrot).

(defun c:KLH-LEVY  () (setq klhylly-last-tyyppi "LEVY")
  (princ "\nHyllytyyppi: LEVY")  (princ))
(defun c:KLH-TIKAS () (setq klhylly-last-tyyppi "TIKAS")
  (princ "\nHyllytyyppi: TIKAS") (princ))

(defun c:KLH-W300 () (setq klhylly-last-levy "300")
  (princ "\nHyllyleveys: 300 mm") (princ))
(defun c:KLH-W400 () (setq klhylly-last-levy "400")
  (princ "\nHyllyleveys: 400 mm") (princ))
(defun c:KLH-W500 () (setq klhylly-last-levy "500")
  (princ "\nHyllyleveys: 500 mm") (princ))

(defun c:KLH-SNAPV () (setq klhylly-last-startmode "V")
  (princ "\nAloituspiste: V (vasen paa)") (princ))
(defun c:KLH-SNAPK () (setq klhylly-last-startmode "K")
  (princ "\nAloituspiste: K (keski)") (princ))

(princ "\nKLH + KLHL + KLHT + KLHV + KORKO ladattu.")
(princ "\nProperties-paletista voi vaihtaa Leveys/Pituus, gripeilla stretchata.")
(princ)
