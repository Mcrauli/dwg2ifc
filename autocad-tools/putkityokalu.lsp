(defun make-layer (name color)
  (if (not (tblsearch "LAYER" name))
    (command "-LAYER" "M" name "C" color "" "")
  )
)

;; 🔹 YKSITTÄISET PUTKET (2 klikkausta)
(defun putki-line (lay vari / p1 p2 oldOrtho)

  ;; ortho talteen + päälle
  (setq oldOrtho (getvar "ORTHOMODE"))
  (setvar "ORTHOMODE" 1)

  ;; layer
  (make-layer lay vari)
  (setvar "CLAYER" lay)

  ;; pisteet
  (setq p1 (getpoint "\nAloituspiste: "))
  (setq p2 (getpoint p1 "\nLoppupiste: "))

  ;; piirrä
  (command "LINE" p1 p2 "")

  ;; palauta ortho
  (setvar "ORTHOMODE" oldOrtho)

  (princ)
)

(defun c:lti () (putki-line "LT IMU" 4))
(defun c:mti () (putki-line "MT IMU" 5))
(defun c:mtn () (putki-line "MT NESTE" 42))


;; 🔥 3 PUTKEA
(defun c:3ptk ( / p1 p2 ent dx dy len nx ny off vecL vecR oldOrtho)

  ;; ortho talteen
  (setq oldOrtho (getvar "ORTHOMODE"))
  (setvar "ORTHOMODE" 1)

  ;; layerit
  (make-layer "MT NESTE" 42)
  (make-layer "LT IMU" 4)
  (make-layer "MT IMU" 5)

  ;; pisteet
  (setq p1 (getpoint "\nAloituspiste: "))
  (setq p2 (getpoint p1 "\nLoppupiste: "))

  ;; keskimmäinen
  (setvar "CLAYER" "MT NESTE")
  (command "LINE" p1 p2 "")
  (setq ent (entlast))

  ;; vektori
  (setq dx (- (car p2) (car p1)))
  (setq dy (- (cadr p2) (cadr p1)))
  (setq len (sqrt (+ (* dx dx) (* dy dy))))

  (setq nx (/ (- dy) len))
  (setq ny (/ dx len))

  (setq off 4)

  (setq vecL (list (* nx off) (* ny off)))
  (setq vecR (list (* (- nx) off) (* (- ny) off)))

  ;; vasen
  (command "COPY" ent "" '(0 0) vecL)
  (command "CHPROP" (entlast) "" "LA" "LT IMU" "")

  ;; oikea
  (command "COPY" ent "" '(0 0) vecR)
  (command "CHPROP" (entlast) "" "LA" "MT IMU" "")

  ;; palauta ortho
  (setvar "ORTHOMODE" oldOrtho)

  (princ)
)