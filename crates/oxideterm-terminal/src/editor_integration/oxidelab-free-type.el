;;; oxidelab-free-type.el --- OxideLab terminal editor integration -*- lexical-binding: t; -*-

;; This adapter reports explicit Emacs/Evil editing state and installs bounded
;; operation keys used only after OxideLab receives a current heartbeat.

(defvar oxidelab-free-type--last-state nil)
(defvar oxidelab-free-type--heartbeat nil)

(defun oxidelab-free-type--private-osc-available-p ()
  "Return non-nil only when private OSC is isolated to an OxideLab session."
  (let ((term-program (downcase (or (getenv "TERM_PROGRAM") "")))
        (lc-terminal (downcase (or (getenv "LC_TERMINAL") ""))))
    (and (= (length (or (getenv "TMUX") "")) 0)
         (= (length (or (getenv "STY") "")) 0)
         (= (length (or (getenv "ZELLIJ") "")) 0)
         (or (equal (getenv "OXIDELAB_PRIVATE_OSC") "1")
             (equal term-program "oxidelab")
             (equal lc-terminal "oxidelab")))))

(defun oxidelab-free-type--write-terminal (payload)
  "Write PAYLOAD only across an isolated OxideLab terminal boundary."
  (when (oxidelab-free-type--private-osc-available-p)
    (send-string-to-terminal payload)))

(defun oxidelab-free-type--mode-name ()
  (if (bound-and-true-p evil-local-mode)
      (pcase evil-state
        ('normal "normal")
        ('insert "insert")
        ('replace "replace")
        ('visual "visual")
        (_ "emacs"))
    "emacs"))

(defun oxidelab-free-type--selection-name ()
  (if (use-region-p) "region" "none"))

(defun oxidelab-free-type--state-payload (active)
  (format "\e]7719;v=3;kind=editor-state;app=emacs;mode=%s;selection=%s;caps=mouse,clipboard,edit;active=%d\a"
          (oxidelab-free-type--mode-name)
          (oxidelab-free-type--selection-name)
          (if active 1 0)))

(defun oxidelab-free-type--emit-state (&optional force)
  (let ((payload (oxidelab-free-type--state-payload t)))
    (when (or force (not (equal payload oxidelab-free-type--last-state)))
      (setq oxidelab-free-type--last-state payload)
      (oxidelab-free-type--write-terminal payload))))

(defun oxidelab-free-type--percent-encode (text)
  ;; Encode every UTF-8 byte so the OSC field grammar never depends on URI
  ;; libraries choosing which printable characters to preserve.
  (mapconcat (lambda (byte) (format "%%%02X" byte))
             (string-to-list (encode-coding-string text 'utf-8))
             ""))

(defun oxidelab-free-type--emit-clipboard (operation text)
  (oxidelab-free-type--write-terminal
   (format "\e]7719;v=3;kind=editor-clipboard;app=emacs;op=%s;data=%s\a"
           operation
           (oxidelab-free-type--percent-encode text))))

(defun oxidelab-free-type-copy-selection ()
  (interactive)
  (when (use-region-p)
    (let ((text (buffer-substring-no-properties
                 (region-beginning) (region-end))))
      (kill-new text)
      (oxidelab-free-type--emit-clipboard "copy" text)))
  (oxidelab-free-type--emit-state t))

(defun oxidelab-free-type-cut-selection ()
  (interactive)
  (when (use-region-p)
    (let ((text (buffer-substring-no-properties
                 (region-beginning) (region-end))))
      (kill-region (region-beginning) (region-end))
      (oxidelab-free-type--emit-clipboard "cut" text)))
  (oxidelab-free-type--emit-state t))

(defun oxidelab-free-type-prepare-paste ()
  (interactive)
  (when (use-region-p)
    (delete-region (region-beginning) (region-end)))
  (oxidelab-free-type--emit-state t))

(defun oxidelab-free-type-delete-selection ()
  (interactive)
  (when (use-region-p)
    (delete-region (region-beginning) (region-end)))
  (oxidelab-free-type--emit-state t))

(defvar oxidelab-free-type-mode-map
  (let ((map (make-sparse-keymap)))
    (define-key map [oxidelab-free-type-copy]
                #'oxidelab-free-type-copy-selection)
    (define-key map [oxidelab-free-type-cut]
                #'oxidelab-free-type-cut-selection)
    (define-key map [oxidelab-free-type-paste]
                #'oxidelab-free-type-prepare-paste)
    (define-key map [oxidelab-free-type-delete]
                #'oxidelab-free-type-delete-selection)
    map))

;;;###autoload
(define-minor-mode oxidelab-free-type-mode
  "Expose explicit terminal editing state to OxideLab Free Type Mode."
  :global t
  :keymap oxidelab-free-type-mode-map
  (if oxidelab-free-type-mode
      (progn
        (define-key input-decode-map "\e[99;5~" [oxidelab-free-type-copy])
        (define-key input-decode-map "\e[99;6~" [oxidelab-free-type-cut])
        (define-key input-decode-map "\e[99;7~" [oxidelab-free-type-paste])
        (define-key input-decode-map "\e[99;8~" [oxidelab-free-type-delete])
        (when (fboundp 'xterm-mouse-mode)
          (xterm-mouse-mode 1))
        (add-hook 'post-command-hook #'oxidelab-free-type--emit-state)
        (setq oxidelab-free-type--heartbeat
              (run-at-time 0 1 #'oxidelab-free-type--emit-state t)))
    (remove-hook 'post-command-hook #'oxidelab-free-type--emit-state)
    (when (timerp oxidelab-free-type--heartbeat)
      (cancel-timer oxidelab-free-type--heartbeat))
    (setq oxidelab-free-type--heartbeat nil)
    (oxidelab-free-type--write-terminal (oxidelab-free-type--state-payload nil))))

(add-hook 'kill-emacs-hook
          (lambda ()
            (when oxidelab-free-type-mode
              (oxidelab-free-type--write-terminal
               (oxidelab-free-type--state-payload nil)))))

(provide 'oxidelab-free-type)
;;; oxidelab-free-type.el ends here
