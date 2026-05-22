;;; _loader.lsp — RadikaTools bundle autoloader
;;;
;;; Tama on AINOA LSP-tiedosto jonka PackageContents.xml merkitsee
;;; LoadOnAutoCADStartup="True":ksi. Tama lataa kaikki muut LSP-
;;; tyokalut absoluuttisella polulla, etsii bundle-juuren itse —
;;; siis ei ole riippuvainen SupportPath:sta tai findfile:sta.
;;;
;;; Lisaksi:
;;;   - Lisaa bundlen Contents/ ja Contents/icons/ AutoCAD:n
;;;     support search path:iin (=> CUIX-ikonit + DWG-blokit loytyy)
;;;   - Tulostaa konsoliin mita ladattiin / mika epaonnistui

(vl-load-com)

;; ============================================================
;; Etsi bundle-juuri
;; ============================================================
;; AutoCAD voi laittaa bundlen useaan kansioon. Yritetaan kaikki
;; standardiseet ApplicationPlugins-polut jarjestyksessa.
(defun rt-find-bundle ( / paths p hit )
  (setq paths
    (list
      (strcat (getenv "APPDATA")     "\\Autodesk\\ApplicationPlugins\\RadikaTools.bundle\\Contents")
      (strcat (getenv "ProgramData") "\\Autodesk\\ApplicationPlugins\\RadikaTools.bundle\\Contents")
      "C:\\Program Files\\Autodesk\\ApplicationPlugins\\RadikaTools.bundle\\Contents"
      "C:\\Program Files (x86)\\Autodesk\\ApplicationPlugins\\RadikaTools.bundle\\Contents"
    ))
  (setq hit nil)
  (foreach p paths
    (if (and (null hit) (findfile (strcat p "\\_loader.lsp")))
      (setq hit p)))
  hit
)

;; ============================================================
;; Lisaa support path:iin (jos ei jo siella) — ActiveX:lla
;; ============================================================
(defun rt-augment-support-path ( newdir / app prefs files curr )
  (setq app   (vlax-get-acad-object))
  (setq prefs (vla-get-Preferences app))
  (setq files (vla-get-Files prefs))
  (setq curr  (vla-get-SupportPath files))
  (if (not (vl-string-search (strcase newdir) (strcase curr)))
    (vla-put-SupportPath files (strcat newdir ";" curr)))
  (princ)
)

;; ============================================================
;; Lataa yksi LSP, paluu T jos onnistui
;; ============================================================
(defun rt-load-one ( base name / full ret )
  (setq full (strcat base "\\" name))
  (if (findfile full)
    (progn
      (setq ret (vl-catch-all-apply 'load (list full)))
      (if (vl-catch-all-error-p ret)
        (progn
          (princ (strcat "\n[RadikaTools] X " name " VIRHE: "
                         (vl-catch-all-error-message ret)))
          nil)
        (progn
          (princ (strcat "\n[RadikaTools] + " name))
          T)))
    (progn
      (princ (strcat "\n[RadikaTools] ? " name " ei loydy: " full))
      nil))
)

;; ============================================================
;; Pamain
;; ============================================================
(princ "\n[RadikaTools] _loader.lsp kaynnissa...")

(setq RT-BASE (rt-find-bundle))

(if (null RT-BASE)
  (princ "\n[RadikaTools] VIRHE: RadikaTools.bundle\\Contents -kansiota ei loydy mistaan ApplicationPlugins-polusta.")
  (progn
    (princ (strcat "\n[RadikaTools] Bundle: " RT-BASE))
    ;; Lisaa support path:iin (DWG-blokit + ikonit loytyy)
    (rt-augment-support-path RT-BASE)
    (rt-augment-support-path (strcat RT-BASE "\\icons"))
    (princ "\n[RadikaTools] Support path paivitetty.")
    ;; Lataa kaikki LSP-tyokalut
    (foreach f '("hoyrystin.lsp" "kaato.lsp" "klhylly.lsp" "positio.lsp"
                 "putkityokalu.lsp" "varusteet.lsp"
                 "kotelo.lsp" "koneikko.lsp" "lauhdutin.lsp")
      (rt-load-one RT-BASE f))
    (princ "\n[RadikaTools] Valmis. Komennot: KLH KLHV KOTELO KORKO MTI LTI MTN POSITIO VPUTKI KAATO VARUSTEET HOYRYSTIN KONEIKKO LAUHDUTIN.")
  ))

(princ "\n")
(princ)
