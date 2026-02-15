# -*- coding: utf-8 -*-
"""
Outil de capture d'image avec contrôle par mot de passe.

Comportement:
- Demande un mot de passe (par défaut dans la variable d'environnement CAPTURE_PASSWORD, sinon "monSecret").
- Si le mot de passe est incorrect: capture une photo depuis la caméra et l'enregistre dans le dossier "photos" avec un horodatage.
- Si le mot de passe est correct: tente d'identifier le visage via face_recognition si la bibliothèque est disponible et des visages de référence existent dans le dossier "faces". Sinon, affiche un message indiquant que la reconnaissance est ignorée.

La dépendance "face_recognition" est optionnelle. Si elle n'est pas installée, le programme fonctionne tout de même (sans reconnaissance faciale).
"""

from __future__ import annotations

import os
import sys
import datetime
import getpass
import cv2

# Import optionnel de face_recognition
try:
    import face_recognition  # type: ignore
    FACE_REC_AVAILABLE = True
except Exception:
    face_recognition = None  # type: ignore
    FACE_REC_AVAILABLE = False


def capture_frame() -> "cv2.Mat":
    """Capture une image depuis la caméra par défaut et retourne la frame BGR.
    Soulève RuntimeError en cas d'échec d'accès ou de lecture.
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Impossible d'accéder à la caméra.")

    try:
        ret, frame = cap.read()
    finally:
        cap.release()

    if not ret or frame is None:
        raise RuntimeError("Échec de la capture depuis la caméra.")

    return frame


def save_image(path: str, frame: "cv2.Mat") -> None:
    """Enregistre l'image BGR au chemin spécifié."""
    ok = cv2.imwrite(path, frame)
    if not ok:
        raise RuntimeError(f"Échec de l'enregistrement de l'image: {path}")


def load_known_faces(folder: str = "faces"):
    """Charge les encodages des visages connus depuis un dossier.

    Le nom de la personne est dérivé du nom de fichier sans extension.
    Seuls les fichiers .jpg/.jpeg/.png sont pris en compte.

    Retourne (encodings, names). Si face_recognition est indisponible, retourne ([], []).
    """
    if not FACE_REC_AVAILABLE:
        return [], []

    if not os.path.isdir(folder):
        return [], []

    valid_exts = (".jpg", ".jpeg", ".png")
    known_encodings = []
    known_names = []

    for filename in os.listdir(folder):
        if not filename.lower().endswith(valid_exts):
            continue
        path = os.path.join(folder, filename)
        try:
            image = face_recognition.load_image_file(path)  # type: ignore[attr-defined]
            encodings = face_recognition.face_encodings(image)  # type: ignore[attr-defined]
            if encodings:
                known_encodings.append(encodings[0])
                known_names.append(os.path.splitext(filename)[0])
        except Exception:
            # Ignore les fichiers corrompus/non lisibles
            continue

    return known_encodings, known_names


essential_msg_rec_ignored = (
    "La bibliothèque 'face_recognition' n'est pas installée. Reconnaissance ignorée."
)


def recognize_face(frame: "cv2.Mat", known_encodings, known_names):
    """Retourne le nom de la personne reconnue ou None.
    Nécessite face_recognition disponible et des encodages connus non vides.
    """
    if not FACE_REC_AVAILABLE or not known_encodings:
        return None

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(rgb_frame)  # type: ignore[attr-defined]
    if not encodings:
        return None

    captured_encoding = encodings[0]
    results = face_recognition.compare_faces(known_encodings, captured_encoding)  # type: ignore[attr-defined]
    if True in results:
        index = results.index(True)
        return known_names[index]
    return None


def main() -> None:
    CORRECT_PASSWORD = os.environ.get("CAPTURE_PASSWORD", "monSecret")

    try:
        password = getpass.getpass("Mot de passe: ")
    except Exception:
        print("Impossible de lire le mot de passe.")
        sys.exit(1)

    if password != CORRECT_PASSWORD:
        # Mot de passe incorrect: capture et enregistre la photo
        try:
            os.makedirs("photos", exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = os.path.join("photos", f"photo_{ts}.png")
            frame = capture_frame()
            save_image(out_path, frame)
            print(f"Mot de passe incorrect — photo enregistrée : {out_path}")
        except Exception as e:
            print("Échec de la capture photo :", e)
        finally:
            sys.exit(1)

    # Mot de passe correct
    print("Mot de passe correct.")

    # Reconnaissance faciale si possible
    if not FACE_REC_AVAILABLE:
        print(essential_msg_rec_ignored)
        return

    known_encodings, known_names = load_known_faces("faces")
    if not known_encodings:
        print("Aucun visage de référence trouvé dans 'faces'. Reconnaissance ignorée.")
        return

    try:
        frame = capture_frame()
        person = recognize_face(frame, known_encodings, known_names)
        if person:
            print(f"Bonne arrivée {person} !")
        else:
            print("Visage inconnu.")
    except Exception as e:
        print("Impossible d'effectuer la reconnaissance faciale :", e)


if __name__ == "__main__":
    main()
