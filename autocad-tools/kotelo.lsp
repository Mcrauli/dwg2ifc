;;; KOTELO.LSP - Kotelon piirtokomento (parametrinen block-instanssi)
;;;
;;; Riippuvuus: rinnalla files/Kotelo.dwg -block-kirjasto, joka sisaltaa
;;; dynamic blockin KOTELO. Block on parametrisoitu: Pituus (Linear,
;;; continuous), muokattavissa Properties-paletissa ja stretchattavissa
;;; gripilla. Leveys ja korkeus tulevat blockista kiinteina.
;;;
;;; Block-geometria on piirretty block-koordinaatistossa niin etta
;;;   +X = pituus  (Pituus-parametrin suunta, insertointipiste alkupaassa)
;;;   +Y = leveys
;;;   +Z = korkeus
;;; Geometria on layerilla 0 (BYBLOCK), joten instanssin layer periytyy
;;; alaspain. Dynamic-blockin rakentaminen: ks. tools/KOTELO-BEDIT-OHJEET.md.
;;;
;;; Lataa: APPLOAD -> valitse tama tiedosto. (Kotelo.dwg loydetaan
;;; automaattisesti samasta kansiosta.)
;;;
;;; Komento:
;;;   KOTELO -> alkupiste -> Z-pudotus +/- (oletus, koska kotelo melkein
;;;             aina tippuu hyllylta alaspain) TAI Enter = pickaa
;;;             loppupiste (vaakakotelo) -> rotaatio (ROTATE live-preview)
;;;
;;; Layer luodaan automaattisesti: KYL-KOTELO, AutoCAD Color Index 175
;;; (RGB 63,63,127) - sama vari kuin muilla KYL-tyokaluilla. IFC-vienti
;;; (dxf2ifc) tunnistaa kotelon KYL-KOTELO-layerista -> IfcCableCarrierSegment
;;; / CABLETRUNKINGSEGMENT.
;;;
;;; Toteutus: dynamic block KOTELO sijoitetaan WCS-origoon
;;; vla-InsertBlock:lla, sitten vla-TransformBy 4x4-matriisilla.
;;; Loppupiste joko lasketaan annetusta Z-pudotuksesta (p2 = p1 + (0,0,dz))
;;; tai pickataan suoraan kun kayttaja painaa Enterin Z-promptissa.
;;; Pituussuunta L tulee p1->p2:sta, korkeus = maailman +Z kohtisuoraksi
;;; tehtyna L:aa vasten (pystypudotuksella fallback maailman +X), leveys
;;; vaakaan kohtisuoraan. Rotaatio tavallisella 2D-ROTATE:lla p1:n
;;; ympari (natiivi dynaaminen preview). Pituus-parametri asetetaan
;;; instanssin pituudeksi. KORKO-komento (klhylly.lsp) toimii koteloon
;;; sellaisenaan (INSERT).

(vl-load-com)

;; ============================================================
;; LAYER-HELPER
;; ============================================================

;; Varmistaa etta layer on olemassa annetulla AutoCAD color index:lla.
;; Jos layer on jo olemassa, ei kosketa sen asetuksiin (kayttajan custom-vari sailyy).
(defun kotelo-ensure-layer ( layerName colorIndex
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
;; BLOCK-DWG LOCATOR (kuvio kopioitu klhylly.lsp:sta)
;; ============================================================

(defun kotelo-self-folder ( / found regbase target ver prod prof appkey val )
  (vl-load-com)
  (setq target "kotelo.lsp")
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

;; Istunnon ajaksi muistettu kansio: jos kayttaja on aiemmin valinnut
;; Kotelo.dwg:n file-dialogilla, sama kansio yritetaan ensin uudelleen.
(if (not (boundp '*kotelo-cached-folder*)) (setq *kotelo-cached-folder* nil))

;; Etsii Kotelo.dwg:n: cached -> Support Path -> self-folder -> yleiset
;; paikat -> file-dialog. Tassa jarjestyksessa, ensimmainen olemassaoleva
;; voittaa. File-dialog-fallback varmistaa ettei locator kaadu vaikka
;; APPLOAD-rekisteri tai ä/ö-polut sotkisivat self-folder-haun.
;; Hakujarjestys: cached -> kotelo.lsp:n oma kansio -> vakioasennus ->
;; yleiset paikat -> findfile -> file-dialog. Paljas findfile on
;; demotettu: se etsii myos avoimen piirustuksen kansiosta, ja
;; samanniminen hajatiedosto kaataisi -INSERTin "block references
;; itself" -virheeseen.
(defun kotelo-find-block-file ( dwgName / cands self found p picked )
  (vl-load-com)
  (setq cands '())
  ;; 1. Aiemmin file-dialogilla valittu kansio (cached istunnon ajaksi)
  (if (and *kotelo-cached-folder* (= (type *kotelo-cached-folder*) 'STR))
    (setq cands (list (strcat *kotelo-cached-folder* "\\" dwgName))))
  ;; 2. kotelo.lsp:n oma kansio
  (if (setq self (kotelo-self-folder))
    (if (= (type self) 'STR)
      (setq cands (append cands (list (strcat self "\\" dwgName))))))
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
  ;; 6. Viimeisena: kayttaja valitsee file-dialogilla. Kansio
  ;;    cachetaan istunnon ajaksi seuraavia KOTELO-ajoja varten.
  (if (null found)
    (progn
      (princ (strcat "\n" dwgName " ei loytynyt — valitse tiedosto file-dialogilla."))
      (setq picked (getfiled (strcat "Etsi " dwgName) dwgName "dwg" 0))
      (if (and picked (= (type picked) 'STR))
        (progn
          (setq found picked)
          (setq *kotelo-cached-folder* (vl-filename-directory picked))
          (princ "\nKansio muistettu istunnon ajaksi.")))))
  found
)

;; ============================================================
;; DYNAMIC BLOCK PROPERTY -SETTERI
;; ============================================================

;; Asettaa dynamic blockin parametrin arvon nimella. Hiljaa epaonnistuu
;; jos parametria ei ole tai arvo ei kelpaa.
(defun kotelo-set-dyn-prop ( ent propName value / obj props p )
  (setq obj (vlax-ename->vla-object ent))
  (setq props (vlax-invoke obj 'GetDynamicBlockProperties))
  (foreach p props
    (if (= (strcase (vla-get-PropertyName p)) (strcase propName))
      (vla-put-Value p (vlax-make-variant value vlax-vbDouble))
    )
  )
)

;; ============================================================
;; KOTELO - kotelo kahden pisteen valiin
;; ============================================================
;; Pick alkupiste -> loppupiste joko klikataan tai valitaan keyword Z
;; ja kirjoitetaan +/- Z-pituus (esim. -2100 = pystykotelo alaspain).
;; Pituussuunta tulee pisteista, korkeus = maailman +Z kohtisuoraksi
;; tehtyna L:aa vasten, leveys vaakaan kohtisuoraan. INSERT WCS-
;; origoon + vla-TransformBy, lopuksi tavallinen ROTATE live-previewlla.

(defun c:KOTELO ( / *error* oldClayer oldCmdecho oldOsmode
                       blockName dwgName blockPath layerName firstTime
                       p1 dz p2 length
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

  (setq blockName "KOTELO")
  (setq dwgName   "Kotelo.dwg")
  (setq layerName "KYL-KOTELO")

  ;; 1) Block-maaritys: ensikerralla lookup vastaavan DWG:n polku
  (setq firstTime (not (tblsearch "BLOCK" blockName)))
  (if firstTime
    (progn
      (setq blockPath (kotelo-find-block-file dwgName))
      (if (null blockPath)
        (progn
          (princ (strcat "\nVIRHE: " dwgName " ei loydy. Varmista etta tiedosto on samassa"))
          (princ "\nkansiossa kuin kotelo.lsp.")
          (exit)
        )
      )
    )
  )

  ;; 2) Alkupiste + Z-pudotus tai loppupisteen pickaus. Kayttotapaus
  ;;    on yleensa pystypudotus (kotelo tippuu hyllylta alaspain), joten
  ;;    Z-numero on oletusprompti — kirjoita esim. -2100. Enter siirtyy
  ;;    pickaamaan loppupisteen (vaakakotelo). getreal palauttaa nilin
  ;;    tyhjasta Enterista ja numeron suoraan kirjoitetusta luvusta —
  ;;    luotettavasti, toisin kuin getpoint+initget 128 -kikkailut.
  (setq p1 (getpoint "\nKotelon alkupiste: "))
  (if (null p1) (exit))
  (setq dz (getreal "\nZ-pudotus +/- (Enter = pickaa loppupiste): "))
  (cond
    ((null dz)
      (setq p2 (getpoint p1 "\nKotelon loppupiste: "))
      (if (null p2) (exit)))
    (t
      (if (< (abs dz) 1.0)
        (progn (princ "\nLiian pieni pituus.") (exit)))
      (setq p2 (list (car p1) (cadr p1) (+ (caddr p1) dz))))
  )

  ;; 3) Pituusakseli L = yksikkovektori p1->p2
  (setq Lraw (mapcar '- p2 p1))
  (setq Lmag (distance '(0.0 0.0 0.0) Lraw))
  (if (< Lmag 1.0)
    (progn (princ "\nPituus liian lyhyt.") (exit)))
  (setq length Lmag)
  (setq L (list (/ (car Lraw)   Lmag)
                (/ (cadr Lraw)  Lmag)
                (/ (caddr Lraw) Lmag)))

  ;; 4) Korkeusakseli D = maailman +Z kohtisuoraksi tehtyna L:aa vasten.
  ;;    Jos L on lahes pystysuora (+Z lahes L:n suuntainen), fallback
  ;;    maailman +X:aan -> kotelo asettuu silti jarkevasti.
  (setq Zw '(0.0 0.0 1.0))
  (setq dotZL (caddr L))                ; Zw . L
  (setq Draw (mapcar '- Zw (list (* dotZL (car L))
                                 (* dotZL (cadr L))
                                 (* dotZL (caddr L)))))
  (setq Dmag (distance '(0.0 0.0 0.0) Draw))
  (if (< Dmag 0.001)
    (progn
      (setq Xw '(1.0 0.0 0.0))
      (setq dotXL (car L))              ; Xw . L
      (setq Draw (mapcar '- Xw (list (* dotXL (car L))
                                     (* dotXL (cadr L))
                                     (* dotXL (caddr L)))))
      (setq Dmag (distance '(0.0 0.0 0.0) Draw))
    )
  )
  (setq D (list (/ (car Draw)   Dmag)
                (/ (cadr Draw)  Dmag)
                (/ (caddr Draw) Dmag)))

  ;; 5) Leveysakseli W = D x L (oikeakatinen kanta: L x W = D)
  (setq W (list
            (- (* (cadr D)  (caddr L)) (* (caddr D) (cadr L)))
            (- (* (caddr D) (car L))   (* (car D)   (caddr L)))
            (- (* (car D)   (cadr L))  (* (cadr D)  (car L)))))

  ;; 6) Layer luonti
  (kotelo-ensure-layer layerName 175)

  ;; 7) Lataa block-maaritys ensikerralla -INSERT:lla origin:iin ja poista
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

  ;; 8) Sijoita instanssi WCS-origoon vla-InsertBlock:lla
  (setq doc (vla-get-ActiveDocument (vlax-get-acad-object)))
  (setq ms  (vla-get-ModelSpace doc))
  (setq ins (vla-InsertBlock ms (vlax-3d-point '(0.0 0.0 0.0))
                             blockName 1.0 1.0 1.0 0.0))

  ;; 8b) Lue blockin bbox -> halfW + halfH. vla-InsertBlock asetti
  ;;     instanssin world-origoon identity-transformilla, joten bbox
  ;;     antaa block-koordinaatiston extentit suoraan: Y = [0..W],
  ;;     Z = [0..H]. Pituuden X-extent vaihtelee mutta ei vaikuta tahan.
  (setq halfW 0.0  halfH 0.0)
  (setq minPt nil  maxPt nil)
  (setq bbRes (vl-catch-all-apply
                'vla-GetBoundingBox (list ins 'minPt 'maxPt)))
  (if (and (not (vl-catch-all-error-p bbRes)) minPt maxPt)
    (progn
      (setq bbMin (vlax-safearray->list minPt))
      (setq bbMax (vlax-safearray->list maxPt))
      (setq halfW (* 0.5 (- (cadr bbMax)  (cadr bbMin))))
      (setq halfH (* 0.5 (- (caddr bbMax) (caddr bbMin))))
    )
  )

  ;; 8c) Anchor = yksi 4:sta kayttajan POINT-pisteesta X=0-paadyssa.
  ;;     Auto-valinta orientaation mukaan, jotta kotelo ei upota:
  ;;     - VAAKAKOTELO (null dz, pickattu loppupiste):
  ;;       anchor = pohjareunan keski (0, halfW, 0).
  ;;       Block Z=0 (pohja) on p1:n tasossa, kotelo lepaa pinnalla.
  ;;     - PYSTYPUDOTUS (dz < 0): anchor = kansireunan keski
  ;;       (0, halfW, H = 2*halfH). Block Z=H (kansi) on p1:n tasossa,
  ;;       kotelo riippuu sen alapuolelta -> ei upota kattoon.
  ;;     - PYSTYNOUSU (dz > 0): anchor = pohjareunan keski.
  ;;       Kotelo nousee p1:lta ylospain.
  ;;     Vasen/oikea-POINTit (Y=0 ja Y=W puolet) jaavat NODe-osnap-
  ;;     targeteiksi seinakiinnityksia varten MOVE-vaiheessa.
  (setq anchorY halfW)
  (setq anchorZ
    (cond
      ((null dz) 0.0)                  ; vaaka -> pohjareunan keski
      ((< dz 0)  (* 2.0 halfH))        ; pudotus -> kansireunan keski
      (t         0.0)))                ; nousu -> pohjareunan keski

  ;; 9) 4x4-muunnos: kanonisen X -> L, Y -> W, Z -> D.
  ;;    Translaatio = p1 - anchorY*W - anchorZ*D, jotta block-koord
  ;;    (0, anchorY, anchorZ) landaa pickattuun pisteeseen p1.
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

  ;; 10) Layer + dynaaminen Pituus-property.
  (vla-put-Layer ins layerName)
  (kotelo-set-dyn-prop (vlax-vla-object->ename ins) "Pituus" length)
  ;; REGEN pakottaa BricsCADin evaluoimaan dynamic-block-actionit — ks.
  ;; klhylly.lsp. AutoCAD hyvaksyy saman REGEN:n harmittomasti.
  (vl-catch-all-apply '(lambda () (command "_.REGEN")))

  ;; 11) Rotaatio: tavallinen 2D-ROTATE p1:n ympari. AutoCAD nayttaa
  ;;     natiivin dynaamisen previewn kun kayttaja liikuttaa hiirta —
  ;;     voi myos kirjoittaa kulman. Esc/Enter = ei kiertoa.
  ;;     vl-catch-all-apply varmistaa ettei Esc keskeyta koko komentoa.
  (setq ename (vlax-vla-object->ename ins))
  (vl-catch-all-apply
    '(lambda ()
       (command "_.ROTATE" ename "" (trans p1 0 1) pause)))

  (setvar "OSMODE"  oldOsmode)
  (setvar "CMDECHO" oldCmdecho)
  (setvar "CLAYER"  oldClayer)

  (princ "\nKOTELO valmis. Properties-paletista voi vaihtaa Pituuden.")
  (princ)
)

(princ "\nKOTELO ladattu. Komento: KOTELO.")
(princ "\nProperties-paletista voi vaihtaa Pituuden, gripilla stretchata.")
(princ)
