(defun c:KAATO3D ( / ent p1 p2 vec len drop kulma axis dir deg mmperm)

  (setq ent (car (entsel "\nValitse objekti: ")))

  (if ent
    (progn
      ;; kysy kaato mm/m
      (setq mmperm (getreal "\nAnna kaato (mm per metri) <5>: "))
      (if (null mmperm) (setq mmperm 5.0))

      ;; pivot
      (setq p1 (getpoint "\nValitse pää joka pysyy paikallaan: "))
      
      ;; suunta
      (setq p2 (getpoint p1 "\nValitse suunta: "))

      ;; vektori
      (setq vec (mapcar '- p2 p1))

      ;; pituus
      (setq len (distance p1 p2))

      ;; kaato
      (setq drop (* (/ len 1000.0) mmperm))

      ;; kulma
      (setq kulma (atan (/ drop len)))
      (setq deg (* kulma (/ 180.0 pi)))

      ;; akseli
      (setq axis (list (- (cadr vec)) (car vec) 0))

      ;; kysy suunta
      (initget "Up Down")
      (setq dir (getkword "\nSuunta [Up/Down] <Up>: "))

      ;; Up = far end nousee, Down = far end laskee.
      ;; Rotaatioakseli (-vec.y, vec.x, 0) + positiivinen rotaatio laskee
      ;; far endia, joten Up tarvitsee negatiivisen degin.
      (if (or (null dir) (= dir "Up"))
        (setq deg (- deg))
      )

      ;; rotaatio — ROTATE3D ottaa kaksi pistetta rotaatioakselille
      ;; suoraan ilman "Axis"-keywordia, joka aiheuttaa BricsCAD:ssa
      ;; akselin tulkinnan menemisen sekaisin (toimii muka 90 asteena).
      (command "ROTATE3D"
               ent ""
               p1                          ; akselin 1. piste
               (mapcar '+ p1 axis)         ; akselin 2. piste
               deg
      )

      (princ (strcat "\nKaato: " (rtos drop 2 2) " mm"))
    )
  )

  (princ)
)
