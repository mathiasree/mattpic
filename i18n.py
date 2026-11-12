# Matt|Pic – Übersetzungen der Oberfläche
# Copyright (C) 2026 Mathias Ree – GPL-3.0-or-later
#
# Schlüssel = deutscher Originaltext aus mattpic.py. Fehlt eine Übersetzung,
# erscheint der deutsche Text. "&" markiert die Alt-Taste im Menü,
# {name} sind Platzhalter, die mattpic.py einsetzt.
# Neue Sprache: Kürzel in LANGUAGES eintragen und in jeder Zeile von ROWS ergänzen.

LANGUAGES = {"de": "Deutsch", "en": "English", "es": "Español", "pt": "Português"}
QT_TRANSLATION = {"de": "de", "en": "en", "es": "es", "pt": "pt_BR"}
THOUSANDS = {"de": ".", "en": ",", "es": ".", "pt": "."}

_lang = "de"


def set_language(lang):
    global _lang
    _lang = lang if lang in LANGUAGES else "en"


def language():
    return _lang


def T(text, **kw):
    s = TR.get(_lang, {}).get(text, text)
    return s.format(**kw) if kw else s


def pick_language(ui_languages):
    """Erste unterstützte Sprache aus der Liste des Systems (z. B. ['es-CL', 'es'])."""
    for name in ui_languages:
        code = name.replace("_", "-").split("-")[0].lower()
        if code in LANGUAGES:
            return code
    return "en"


# (Deutsch, English, Español, Português)
ROWS = [
    # --- Hauptfenster: Leiste oben
    ("＋  Ordner hinzufügen", "＋  Add folder", "＋  Añadir carpeta", "＋  Adicionar pasta"),
    ("Gruppieren:", "Group:", "Agrupar:", "Agrupar:"),
    ("Nach Ordner", "By folder", "Por carpeta", "Por pasta"),
    ("Nach Monat", "By month", "Por mes", "Por mês"),
    ("Nach Jahr", "By year", "Por año", "Por ano"),
    ("Sortieren:", "Sort:", "Ordenar:", "Ordenar:"),
    ("Datum, neueste zuerst", "Date, newest first", "Fecha, más recientes primero", "Data, mais recentes primeiro"),
    ("Datum, älteste zuerst", "Date, oldest first", "Fecha, más antiguas primero", "Data, mais antigas primeiro"),
    ("Name", "Name", "Nombre", "Nome"),
    ("Größe", "Size", "Tamaño", "Tamanho"),
    ("Sterne", "Stars", "Estrellas", "Estrelas"),
    ("Mindestens:", "At least:", "Mínimo:", "Mínimo:"),
    ("alle", "all", "todas", "todas"),
    ("Suchen …", "Search …", "Buscar …", "Pesquisar …"),
    # --- Hauptfenster: Leiste unten, Zähler
    ("Ablage: nichts ausgewählt", "Tray: nothing selected", "Bandeja: nada seleccionado", "Bandeja: nada selecionado"),
    ("Links drehen (Strg+Umschalt+R)", "Rotate left (Ctrl+Shift+R)", "Girar a la izquierda (Ctrl+Mayús+R)",
     "Girar para a esquerda (Ctrl+Shift+R)"),
    ("Rechts drehen (Strg+R)", "Rotate right (Ctrl+R)", "Girar a la derecha (Ctrl+R)", "Girar para a direita (Ctrl+R)"),
    ("Stern setzen oder entfernen (Tasten 0 bis 5)", "Set or remove star (keys 0 to 5)",
     "Poner o quitar estrella (teclas 0 a 5)", "Marcar ou remover estrela (teclas 0 a 5)"),
    ("Verschieben (M)", "Move (M)", "Mover (M)", "Mover (M)"),
    ("Exportieren (E)", "Export (E)", "Exportar (E)", "Exportar (E)"),
    ("Papierkorb", "Trash", "Papelera", "Lixeira"),
    ("Größe der Vorschaubilder", "Thumbnail size", "Tamaño de las miniaturas", "Tamanho das miniaturas"),
    ("1 Foto", "1 photo", "1 foto", "1 foto"),
    ("{n} Fotos", "{n} photos", "{n} fotos", "{n} fotos"),
    ("Vorschaubilder: noch {n}", "Thumbnails: {n} left", "Miniaturas: faltan {n}", "Miniaturas: faltam {n}"),
    ("Keine Fotos gefunden.\n\nFüge über „Ordner hinzufügen“ einen Foto-Ordner hinzu\noder ändere den Filter.",
     "No photos found.\n\nAdd a photo folder with “Add folder”\nor change the filter.",
     "No se encontraron fotos.\n\nAñade una carpeta de fotos con «Añadir carpeta»\no cambia el filtro.",
     "Nenhuma foto encontrada.\n\nAdicione uma pasta de fotos em “Adicionar pasta”\nou altere o filtro."),
    ("Noch keine Ordner: Über „Ordner hinzufügen“ geht es los.", "No folders yet: start with “Add folder”.",
     "Aún no hay carpetas: empieza con «Añadir carpeta».", "Ainda não há pastas: comece em “Adicionar pasta”."),
    ("Durchsuche Ordner … {n} Dateien", "Scanning folders … {n} files", "Explorando carpetas … {n} archivos",
     "Examinando pastas … {n} arquivos"),
    ("Lese Aufnahmedaten … {done} von {total}", "Reading capture dates … {done} of {total}",
     "Leyendo fechas de captura … {done} de {total}", "Lendo datas de captura … {done} de {total}"),
    ("{name} (nicht erreichbar)", "{name} (not available)", "{name} (no disponible)", "{name} (indisponível)"),
    ("Nicht erreichbar: ", "Not available: ", "No disponible: ", "Indisponível: "),
    ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y"),
    ("{a} bis {b}", "{a} to {b}", "{a} a {b}", "{a} a {b}"),
    # --- Monate
    ("Januar", "January", "Enero", "Janeiro"), ("Februar", "February", "Febrero", "Fevereiro"),
    ("März", "March", "Marzo", "Março"), ("April", "April", "Abril", "Abril"), ("Mai", "May", "Mayo", "Maio"),
    ("Juni", "June", "Junio", "Junho"), ("Juli", "July", "Julio", "Julho"), ("August", "August", "Agosto", "Agosto"),
    ("September", "September", "Septiembre", "Setembro"), ("Oktober", "October", "Octubre", "Outubro"),
    ("November", "November", "Noviembre", "Novembro"), ("Dezember", "December", "Diciembre", "Dezembro"),
    # --- Menüs
    ("&Datei", "&File", "&Archivo", "&Arquivo"),
    ("Ordner hinzufügen …", "Add folder …", "Añadir carpeta …", "Adicionar pasta …"),
    ("Ordner neu einlesen", "Rescan folders", "Volver a leer carpetas", "Reler pastas"),
    ("Exportieren …", "Export …", "Exportar …", "Exportar …"),
    ("Beenden", "Quit", "Salir", "Sair"),
    ("&Bearbeiten", "&Edit", "&Editar", "&Editar"),
    ("Rückgängig", "Undo", "Deshacer", "Desfazer"),
    ("Alles auswählen", "Select all", "Seleccionar todo", "Selecionar tudo"),
    ("Auswahl aufheben", "Clear selection", "Quitar selección", "Limpar seleção"),
    ("Suchen", "Search", "Buscar", "Pesquisar"),
    ("&Foto", "&Photo", "&Foto", "&Foto"),
    ("Keine Sterne", "No stars", "Sin estrellas", "Sem estrelas"),
    ("Rechts drehen", "Rotate right", "Girar a la derecha", "Girar para a direita"),
    ("Links drehen", "Rotate left", "Girar a la izquierda", "Girar para a esquerda"),
    ("In Ordner verschieben …", "Move to folder …", "Mover a carpeta …", "Mover para pasta …"),
    ("In den Papierkorb", "Move to trash", "Mover a la papelera", "Mover para a lixeira"),
    ("Im Dateimanager zeigen", "Show in file manager", "Mostrar en el gestor de archivos", "Mostrar no gerenciador de arquivos"),
    ("Öffnen mit", "Open with", "Abrir con", "Abrir com"),
    ("Öffnen", "Open", "Abrir", "Abrir"),
    ("&Hilfe", "&Help", "Ay&uda", "Aj&uda"),
    ("Tastenkürzel", "Keyboard shortcuts", "Atajos de teclado", "Atalhos de teclado"),
    ("Sprache der Oberfläche", "Interface language", "Idioma de la interfaz", "Idioma da interface"),
    ("Systemsprache ({lang})", "System language ({lang})", "Idioma del sistema ({lang})", "Idioma do sistema ({lang})"),
    ("Die neue Sprache gilt nach einem Neustart von Matt|Pic.", "The new language applies after restarting Matt|Pic.",
     "El nuevo idioma se aplica al reiniciar Matt|Pic.", "O novo idioma vale após reiniciar o Matt|Pic."),
    ("Über Matt|Pic", "About Matt|Pic", "Acerca de Matt|Pic", "Sobre o Matt|Pic"),
    ("Fotos schnell sortieren und bearbeiten.", "Sort and touch up photos quickly.",
     "Ordenar y retocar fotos rápidamente.", "Organizar e retocar fotos rapidamente."),
    ("Erst ein Foto auswählen", "Select a photo first", "Selecciona primero una foto", "Selecione uma foto primeiro"),
    ("Erst Fotos auswählen", "Select photos first", "Selecciona primero las fotos", "Selecione as fotos primeiro"),
    ("Anderes Programm …", "Other application …", "Otro programa …", "Outro programa …"),
    ("Standardprogramm", "Default application", "Programa predeterminado", "Programa padrão"),
    ("Programm:", "Application:", "Programa:", "Programa:"),
    ("In {app} geöffnet. Speicherst du dort, kommt die Änderung hier automatisch an.",
     "Opened in {app}. If you save there, the change shows up here automatically.",
     "Abierto en {app}. Si guardas allí, el cambio aparece aquí automáticamente.",
     "Aberto no {app}. Se você salvar lá, a alteração aparece aqui automaticamente."),
    ("{app} ließ sich nicht starten.", "{app} could not be started.", "No se pudo iniciar {app}.",
     "Não foi possível iniciar o {app}."),
    # --- Ordnerliste
    ("Foto-Ordner hinzufügen", "Add photo folder", "Añadir carpeta de fotos", "Adicionar pasta de fotos"),
    ("Der Ordner gehört schon zur Bibliothek: {path}", "The folder is already in the library: {path}",
     "La carpeta ya está en la biblioteca: {path}", "A pasta já está na biblioteca: {path}"),
    ("Ordner entfernen", "Remove folder", "Quitar carpeta", "Remover pasta"),
    ("„{name}“ aus Matt|Pic entfernen?\n\nDie Dateien bleiben unberührt. Sterne und Korrekturen dieses Ordners gehen verloren.",
     "Remove “{name}” from Matt|Pic?\n\nThe files stay untouched. Stars and corrections in this folder will be lost.",
     "¿Quitar «{name}» de Matt|Pic?\n\nLos archivos no se tocan. Se perderán las estrellas y correcciones de esta carpeta.",
     "Remover “{name}” do Matt|Pic?\n\nOs arquivos não são alterados. As estrelas e correções desta pasta serão perdidas."),
    ("Neuer Unterordner …", "New subfolder …", "Nueva subcarpeta …", "Nova subpasta …"),
    ("Im Dateimanager öffnen", "Open in file manager", "Abrir en el gestor de archivos", "Abrir no gerenciador de arquivos"),
    ("Aus Matt|Pic entfernen …", "Remove from Matt|Pic …", "Quitar de Matt|Pic …", "Remover do Matt|Pic …"),
    ("Neuer Ordner", "New folder", "Nueva carpeta", "Nova pasta"),
    ("Name:", "Name:", "Nombre:", "Nome:"),
    ("Ungültiger Ordnername", "Invalid folder name", "Nombre de carpeta no válido", "Nome de pasta inválido"),
    ("Ordner konnte nicht angelegt werden:", "Could not create the folder:", "No se pudo crear la carpeta:",
     "Não foi possível criar a pasta:"),
    # --- Verschieben, Papierkorb, Rückgängig
    ("Verschieben", "Move", "Mover", "Mover"),
    ("1 Foto verschieben nach:", "Move 1 photo to:", "Mover 1 foto a:", "Mover 1 foto para:"),
    ("{n} Fotos verschieben nach:", "Move {n} photos to:", "Mover {n} fotos a:", "Mover {n} fotos para:"),
    ("Ordner suchen …", "Find folder …", "Buscar carpeta …", "Procurar pasta …"),
    ("Kopiere …", "Copying …", "Copiando …", "Copiando …"),
    ("Verschiebe …", "Moving …", "Moviendo …", "Movendo …"),
    ("Abbrechen", "Cancel", "Cancelar", "Cancelar"),
    ("Nicht alles hat geklappt:", "Not everything worked:", "No todo salió bien:", "Nem tudo deu certo:"),
    ("{n} kopiert", "{n} copied", "{n} copiadas", "{n} copiadas"),
    ("{n} nach „{folder}“ verschoben. Strg+Z macht es rückgängig.",
     "{n} moved to “{folder}”. Ctrl+Z undoes it.",
     "{n} movidas a «{folder}». Ctrl+Z lo deshace.",
     "{n} movidas para “{folder}”. Ctrl+Z desfaz."),
    ("{n} zurückverschoben", "{n} moved back", "{n} devueltas a su lugar", "{n} devolvidas ao lugar"),
    ("Konnte nicht in den Papierkorb (z. B. auf Netzlaufwerken):",
     "Could not move to trash (e.g. on network drives):",
     "No se pudo mover a la papelera (p. ej. en unidades de red):",
     "Não foi possível mover para a lixeira (p. ex. em unidades de rede):"),
    ("{n} im Papierkorb. Strg+Z holt sie zurück.", "{n} moved to trash. Ctrl+Z brings them back.",
     "{n} en la papelera. Ctrl+Z las recupera.", "{n} na lixeira. Ctrl+Z as recupera."),
    ("Nichts mehr rückgängig zu machen", "Nothing left to undo", "No queda nada por deshacer", "Nada mais para desfazer"),
    # --- Export
    ("Exportieren", "Export", "Exportar", "Exportar"),
    ("1 Foto wird mit den Korrekturen als neue Datei gespeichert.\nDie Originale bleiben unverändert.",
     "1 photo will be saved with the corrections as a new file.\nThe originals stay unchanged.",
     "1 foto se guardará con las correcciones como archivo nuevo.\nLos originales no se modifican.",
     "1 foto será salva com as correções como um novo arquivo.\nOs originais não são alterados."),
    ("{n} Fotos werden mit den Korrekturen als neue Dateien gespeichert.\nDie Originale bleiben unverändert.",
     "{n} photos will be saved with the corrections as new files.\nThe originals stay unchanged.",
     "{n} fotos se guardarán con las correcciones como archivos nuevos.\nLos originales no se modifican.",
     "{n} fotos serão salvas com as correções como novos arquivos.\nOs originais não são alterados."),
    ("Wählen …", "Choose …", "Elegir …", "Escolher …"),
    ("Zielordner:", "Destination:", "Carpeta de destino:", "Pasta de destino:"),
    ("Zielordner", "Destination folder", "Carpeta de destino", "Pasta de destino"),
    ("Originalgröße", "Original size", "Tamaño original", "Tamanho original"),
    ("{n} Pixel", "{n} pixels", "{n} píxeles", "{n} pixels"),
    ("Längste Seite:", "Longest side:", "Lado más largo:", "Lado maior:"),
    ("Hoch (92)", "High (92)", "Alta (92)", "Alta (92)"),
    ("Sehr hoch (97)", "Very high (97)", "Muy alta (97)", "Muito alta (97)"),
    ("Mittel (82)", "Medium (82)", "Media (82)", "Média (82)"),
    ("JPEG-Qualität:", "JPEG quality:", "Calidad JPEG:", "Qualidade JPEG:"),
    ("Zielordner geht nicht:", "Destination folder not usable:", "No se puede usar la carpeta de destino:",
     "Não é possível usar a pasta de destino:"),
    ("Exportiere …", "Exporting …", "Exportando …", "Exportando …"),
    ("{n} exportiert nach {dest}", "{n} exported to {dest}", "{n} exportadas a {dest}", "{n} exportadas para {dest}"),
    # --- Großansicht
    ("◀  Zurück zur Bibliothek", "◀  Back to library", "◀  Volver a la biblioteca", "◀  Voltar à biblioteca"),
    ("Korrekturen", "Corrections", "Correcciones", "Correções"),
    ("Feinabstimmung", "Fine-tuning", "Ajuste fino", "Ajuste fino"),
    ("Zuschneiden (C)", "Crop (C)", "Recortar (C)", "Recortar (C)"),
    ("Freies Format", "Free ratio", "Proporción libre", "Proporção livre"),
    ("Originalformat", "Original ratio", "Proporción original", "Proporção original"),
    ("Übernehmen", "Apply", "Aplicar", "Aplicar"),
    ("Zuschnitt entfernen", "Remove crop", "Quitar recorte", "Remover recorte"),
    ("Automatik (A)", "Auto (A)", "Automático (A)", "Automático (A)"),
    ("Auto-Kontrast", "Auto contrast", "Contraste automático", "Contraste automático"),
    ("Auto-Farbe", "Auto colour", "Color automático", "Cor automática"),
    ("Aufhellen", "Fill light", "Aclarar", "Clarear"),
    ("Begradigen", "Straighten", "Enderezar", "Endireitar"),
    ("Lichter", "Highlights", "Luces", "Realces"),
    ("Schatten", "Shadows", "Sombras", "Sombras"),
    ("Farbtemperatur", "Colour temperature", "Temperatura de color", "Temperatura de cor"),
    ("Sättigung", "Saturation", "Saturación", "Saturação"),
    ("Alles zurück", "Reset all", "Restablecer todo", "Redefinir tudo"),
    ("Pfad kopieren", "Copy path", "Copiar ruta", "Copiar caminho"),
    ("Kopiert ✓", "Copied ✓", "Copiado ✓", "Copiado ✓"),
    ("Vollständige Adresse in die Zwischenablage kopieren", "Copy the full path to the clipboard",
     "Copiar la ruta completa al portapapeles", "Copiar o caminho completo para a área de transferência"),
    ("Verkleinern (Taste − oder Mausrad)", "Zoom out (key − or mouse wheel)", "Alejar (tecla − o rueda del ratón)",
     "Diminuir zoom (tecla − ou roda do mouse)"),
    ("Vergrößern (Taste + oder Mausrad)", "Zoom in (key + or mouse wheel)", "Acercar (tecla + o rueda del ratón)",
     "Aumentar zoom (tecla + ou roda do mouse)"),
    ("Einpassen", "Fit", "Ajustar", "Ajustar"),
    ("Ganzes Bild zeigen (Taste F)", "Show whole image (key F)", "Mostrar la imagen completa (tecla F)",
     "Mostrar a imagem inteira (tecla F)"),
    ("{i} von {n}", "{i} of {n}", "{i} de {n}", "{i} de {n}"),
    # --- EXIF
    ("<p>Lese Metadaten …</p>", "<p>Reading metadata …</p>", "<p>Leyendo metadatos …</p>", "<p>Lendo metadados …</p>"),
    ("<p>Keine Metadaten gefunden.</p>", "<p>No metadata found.</p>", "<p>No se encontraron metadatos.</p>",
     "<p>Nenhum metadado encontrado.</p>"),
    ("exiftool ist nicht installiert (Paket perl-image-exiftool).", "exiftool is not installed.",
     "exiftool no está instalado.", "O exiftool não está instalado."),
    ("exiftool hat zu lange gebraucht.", "exiftool took too long.", "exiftool tardó demasiado.", "O exiftool demorou demais."),
    ("Die Metadaten konnten nicht gelesen werden.", "The metadata could not be read.", "No se pudieron leer los metadatos.",
     "Não foi possível ler os metadados."),
    ("Alle Daten", "All data", "Todos los datos", "Todos os dados"),
    ("Aufnahme", "Capture", "Captura", "Captura"),
    ("Datum", "Date", "Fecha", "Data"),
    ("Hersteller", "Make", "Fabricante", "Fabricante"),
    ("Kamera", "Camera", "Cámara", "Câmera"),
    ("Bildgröße", "Image size", "Tamaño de imagen", "Tamanho da imagem"),
    ("Dauer", "Duration", "Duración", "Duração"),
    ("Bildrate", "Frame rate", "Fotogramas por segundo", "Taxa de quadros"),
    ("Belichtung", "Exposure", "Exposición", "Exposição"),
    ("Blende", "Aperture", "Apertura", "Abertura"),
    ("ISO", "ISO", "ISO", "ISO"),
    ("Brennweite", "Focal length", "Distancia focal", "Distância focal"),
    ("Kleinbild", "35 mm equivalent", "Equivalente 35 mm", "Equivalente 35 mm"),
    ("Korrektur", "Exposure comp.", "Compensación", "Compensação"),
    ("Weißabgleich", "White balance", "Balance de blancos", "Balanço de branco"),
    ("Firmware", "Firmware", "Firmware", "Firmware"),
    ("Ort", "Location", "Ubicación", "Local"),
    ("Position", "Position", "Posición", "Posição"),
    ("Höhe ü. Meer", "Altitude (sea level)", "Altitud s. n. m.", "Altitude (nível do mar)"),
    ("Höhe ü. Start", "Height above takeoff", "Altura sobre despegue", "Altura sobre a decolagem"),
    ("Drohne", "Drone", "Dron", "Drone"),
    ("Gieren", "Yaw", "Guiñada", "Guinada"),
    ("Nicken", "Pitch", "Cabeceo", "Arfagem"),
    ("Rollen", "Roll", "Alabeo", "Rolagem"),
    ("Gimbal Gieren", "Gimbal yaw", "Guiñada del gimbal", "Guinada do gimbal"),
    ("Gimbal Nicken", "Gimbal pitch", "Cabeceo del gimbal", "Arfagem do gimbal"),
    ("Gimbal Rollen", "Gimbal roll", "Alabeo del gimbal", "Rolagem do gimbal"),
    ("Tempo X", "Speed X", "Velocidad X", "Velocidade X"),
    ("Tempo Y", "Speed Y", "Velocidad Y", "Velocidade Y"),
    ("Tempo Z", "Speed Z", "Velocidad Z", "Velocidade Z"),
    # --- Fehler
    ("Interner Fehler: {error} (Details in fehler.log)", "Internal error: {error} (details in fehler.log)",
     "Error interno: {error} (detalles en fehler.log)", "Erro interno: {error} (detalhes em fehler.log)"),
]

_HELP_ROWS = [
    # (Taste, Deutsch, English, Español, Português); Taste None = Zwischenüberschrift
    (("0 … 5",) * 4, "Sterne setzen", "Set stars", "Poner estrellas", "Marcar estrelas"),
    (("Pfeile", "Arrows", "Flechas", "Setas"), "Foto wechseln (Umschalt: Bereich auswählen)",
     "Change photo (Shift: select range)", "Cambiar de foto (Mayús: seleccionar rango)",
     "Trocar de foto (Shift: selecionar intervalo)"),
    (("Enter",) * 4, "Foto öffnen", "Open photo", "Abrir foto", "Abrir foto"),
    (("Esc",) * 4, "Zurück zur Bibliothek", "Back to library", "Volver a la biblioteca", "Voltar à biblioteca"),
    (("M",) * 4, "In einen Ordner verschieben (tippen, Enter)", "Move to a folder (type, Enter)",
     "Mover a una carpeta (escribir, Enter)", "Mover para uma pasta (digitar, Enter)"),
    (("Entf", "Del", "Supr", "Del"), "In den Papierkorb", "Move to trash", "Mover a la papelera", "Mover para a lixeira"),
    (("Strg+R, Strg+Umschalt+R", "Ctrl+R, Ctrl+Shift+R", "Ctrl+R, Ctrl+Mayús+R", "Ctrl+R, Ctrl+Shift+R"),
     "Rechts, links drehen", "Rotate right, left", "Girar a la derecha, a la izquierda", "Girar para a direita, esquerda"),
    (("E",) * 4, "Exportieren", "Export", "Exportar", "Exportar"),
    (("Strg+Z", "Ctrl+Z", "Ctrl+Z", "Ctrl+Z"), "Rückgängig", "Undo", "Deshacer", "Desfazer"),
    (("Strg+F", "Ctrl+F", "Ctrl+F", "Ctrl+F"), "Suchen", "Search", "Buscar", "Pesquisar"),
    (("Strg+A", "Ctrl+A", "Ctrl+A", "Ctrl+A"), "Alles auswählen", "Select all", "Seleccionar todo", "Selecionar tudo"),
    (("F5",) * 4, "Ordner neu einlesen", "Rescan folders", "Volver a leer carpetas", "Reler pastas"),
    (("Strg+Mausrad", "Ctrl+mouse wheel", "Ctrl+rueda del ratón", "Ctrl+roda do mouse"),
     "Vorschaubilder größer oder kleiner", "Larger or smaller thumbnails", "Miniaturas más grandes o más pequeñas",
     "Miniaturas maiores ou menores"),
    (("Rechtsklick", "Right-click", "Clic derecho", "Clique direito"), "Öffnen mit …, z. B. PhotoCraft",
     "Open with …, e.g. PhotoCraft", "Abrir con …, p. ej. PhotoCraft", "Abrir com …, p. ex. PhotoCraft"),
    (None, "In der Großansicht", "In the large view", "En la vista grande", "Na visualização ampliada"),
    (("Leertaste", "Space", "Espacio", "Espaço"), "Nächstes Foto", "Next photo", "Foto siguiente", "Próxima foto"),
    (("C",) * 4, "Zuschneiden (Enter übernimmt)", "Crop (Enter applies)", "Recortar (Enter aplica)",
     "Recortar (Enter aplica)"),
    (("A",) * 4, "Automatik", "Auto", "Automático", "Automático"),
    (("Mausrad, + und −", "Mouse wheel, + and −", "Rueda del ratón, + y −", "Roda do mouse, + e −"),
     "Hinein- und herauszoomen, Ziehen verschiebt das Bild", "Zoom in and out, drag to pan",
     "Acercar y alejar, arrastrar mueve la imagen", "Aumentar e diminuir zoom, arrastar move a imagem"),
    (("Z, Doppelklick", "Z, double-click", "Z, doble clic", "Z, clique duplo"), "100 % oder einpassen",
     "100 % or fit", "100 % o ajustar", "100 % ou ajustar"),
    (("F",) * 4, "Ganzes Bild zeigen", "Show whole image", "Mostrar la imagen completa", "Mostrar a imagem inteira"),
    (None, "In der Ordnerliste", "In the folder list", "En la lista de carpetas", "Na lista de pastas"),
    (("Fotos hineinziehen", "Drag photos onto it", "Arrastrar fotos", "Arrastar fotos"),
     "Verschieben (mit Strg: Kopieren)", "Move (with Ctrl: copy)", "Mover (con Ctrl: copiar)", "Mover (com Ctrl: copiar)"),
]
_HELP_TEXT = (
    ("Matt|Pic: Tastenkürzel", "Matt|Pic: keyboard shortcuts", "Matt|Pic: atajos de teclado", "Matt|Pic: atalhos de teclado"),
    ("Die Originale werden nie verändert. Sterne und Korrekturen stehen in der Datenbank von Matt|Pic.",
     "The originals are never changed. Stars and corrections are kept in Matt|Pic's database.",
     "Los originales nunca se modifican. Las estrellas y correcciones se guardan en la base de datos de Matt|Pic.",
     "Os originais nunca são alterados. As estrelas e correções ficam no banco de dados do Matt|Pic."),
)


def help_html(i):
    rows = []
    for keys, *texts in _HELP_ROWS:
        if keys is None:
            rows.append(f"<tr><td colspan=2><br><b>{texts[i]}</b></td></tr>")
        else:
            rows.append(f"<tr><td><b>{keys[i]}</b></td><td>{texts[i]}</td></tr>")
    return (f"<h3>{_HELP_TEXT[0][i]}</h3>\n<table cellspacing=4>\n" + "\n".join(rows) +
            f"\n</table>\n<p>{_HELP_TEXT[1][i]}</p>")


HELP_KEY = "HELP"       # mattpic.py zeigt T(HELP_KEY)

TR = {code: {row[0]: row[i] for row in ROWS} for i, code in enumerate(LANGUAGES) if code != "de"}
for _i, _code in enumerate(LANGUAGES):
    TR.setdefault(_code, {})[HELP_KEY] = help_html(_i)
