# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import datetime
from typing import Optional

from flask import Flask, render_template, request, redirect, url_for

# Importer les fonctions utilitaires depuis votre module existant
import captu_image as core

app = Flask(__name__)


def verify_password_and_act(submitted_password: str) -> dict:
    """Vérifie le mot de passe et applique les actions définies dans le module core.

    Retourne un dict avec les clés:
      - status: "ok" ou "error"
      - message: message utilisateur
      - photo_path: chemin du fichier photo si une photo a été prise
      - person: nom reconnu si visage identifié
    """
    result = {
        "status": "ok",
        "message": "",
        "photo_path": None,
        "person": None,
    }

    correct_password = os.environ.get("CAPTURE_PASSWORD", "monSecret")

    if submitted_password != correct_password:
        # Mot de passe incorrect — prendre une photo et l'enregistrer
        try:
            os.makedirs("photos", exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = os.path.join("photos", f"photo_{ts}.png")
            frame = core.capture_frame()
            core.save_image(out_path, frame)
            result["message"] = f"Mot de passe incorrect — photo enregistrée : {out_path}"
            result["photo_path"] = out_path
            result["status"] = "error"
            return result
        except Exception as e:
            result["status"] = "error"
            result["message"] = f"Échec de la capture photo : {e}"
            return result

    # Mot de passe correct — tentative de reconnaissance faciale si disponible
    if not getattr(core, "FACE_REC_AVAILABLE", False):
        result["message"] = (
            "Mot de passe correct. La bibliothèque 'face_recognition' n'est pas installée. "
            "Reconnaissance ignorée."
        )
        return result

    known_encodings, known_names = core.load_known_faces("faces")
    if not known_encodings:
        result["message"] = (
            "Mot de passe correct. Aucun visage de référence trouvé dans 'faces'. Reconnaissance ignorée."
        )
        return result

    try:
        frame = core.capture_frame()
        person = core.recognize_face(frame, known_encodings, known_names)
        if person:
            result["message"] = f"Mot de passe correct. Bonne arrivée {person} !"
            result["person"] = person
        else:
            result["message"] = "Mot de passe correct. Visage inconnu."
        return result
    except Exception as e:
        result["message"] = f"Mot de passe correct. Impossible d'effectuer la reconnaissance : {e}"
        return result


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/submit")
def submit():
    password = request.form.get("password", "")
    res = verify_password_and_act(password)
    # Rendre une page résultat avec le message et éventuellement le lien vers la photo
    return render_template("result.html", **res)


if __name__ == "__main__":
    # Par défaut en développement
    app.run(host="127.0.0.1", port=5000, debug=True)
