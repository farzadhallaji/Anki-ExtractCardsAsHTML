from aqt import mw, utils
from aqt.qt import *
from os.path import expanduser, join
import os
import base64
import re

html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
    {{style}}
    button.audio-btn {
        background: url('data:image/svg+xml;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAACXBIWXMAAAsTAAALEwEAmpwYAAABTklEQVRoge3ZvUtCYRQG8JeEaAkXaQyaG9obdFVy16nRtdG1waHVxT/A0dVR0N2gZlehTWiJqKDsOeIBwc977+t7fOQ+8NvPA/fj3Pc6lybNXpOxHiBJqvANLcgZzxIrDZjOvUMdTk0nipjFAmoEZcuhomRVAdWDa7vRdsumAuIHmpC1GnBbthVQE3hwB/jE2rWAeoWCyaRrErWA6sKVwbxLiVtAyPtD7o/z4FMvJEkB9QY1OAk8+yw+CqhnuA07vt8C4g86cMlaQH3AI5yxFlBjuGcuoAZww1xA/EIbLlgLKK9ru0UB5WVttyygEq3th1BAyFpSYi9QZC1AewnJTXwXd3DLArSPUeoXWd+RrhK0yxztOk39QTN0pJ+UtB/1n/DkSI9VaA+2XiBvMumaHP3hLvXxOu0PDi9rbqjQ/+SrwJcj/s0qMXmDpkkTMP8s/ucrc9kEaQAAAABJRU5ErkJggg==') no-repeat center center; /* Base64-encoded play icon */
        width: 32px;
        height: 32px;
        border: none;
        cursor: pointer;
    }
    button.audio-btn:focus {
        outline: none;
    }
    </style>
</head>
<body>
    {{body}}

    <script>
        function playAudio(id) {
            var audio = document.getElementById(id);
            if (audio.paused) {
                audio.play();
            } else {
                audio.pause();
            }
        }
    </script>
</body>
</html>
"""

class ExportToHtmlDialog(QDialog):
    def __init__(self):
        super().__init__(mw)
        self.setWindowTitle("Export Deck to HTML")
        self.deck_selection = QComboBox()
        self.deck_selection.addItems(mw.col.decks.allNames())
        
        self.save_btn = QPushButton("Export")
        self.save_btn.clicked.connect(self.export_to_html)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select a Deck"))
        layout.addWidget(self.deck_selection)
        layout.addWidget(self.save_btn)
        self.setLayout(layout)

    def export_to_html(self):
        # Get selected deck
        deck_name = self.deck_selection.currentText()
        query = f'deck:"{deck_name}"'
        cids = mw.col.findCards(query)

        # Select directory path using QFileDialog
        directory = QFileDialog.getExistingDirectory(self, "Select Directory", expanduser("~/Desktop"))

        if not directory:
            utils.showInfo("No directory selected.")
            return

        # Build HTML content and save each card to a separate HTML file
        self.save_cards_as_html(cids, directory)

    def save_cards_as_html(self, cids, directory):
        errors = []
        for i, cid in enumerate(cids):
            card = mw.col.getCard(cid)
            note = card.note()
            model = note.model()

            # Extract the CSS from the card's note model (card template)
            css = model.get('css', '')

            # Build the HTML for the card
            card_html = f"<div><h3>Card {i+1}</h3>\n"
            for field_name in note.keys():
                value = note[field_name].strip()  # Strip whitespace
                if value:  # Only include non-empty fields
                    value = re.sub(r'{{[c|C][0-9]+::(.*?)}}', r'\1', value)  # Handle cloze deletion
                    card_html += f"<div><strong>{field_name}:</strong> {self.process_media(value)}</div>\n"
            card_html += "<hr/></div>"
            card_html = html_template.replace("{{style}}", css).replace("{{body}}", card_html)

            # Determine the filename based on a field value or index
            filename = f"card_{i+1}.html"
            field_name_for_filename = list(note.keys())[0]  # Optionally use the first field as the filename
            if note[field_name_for_filename].strip():
                filename = f"{note[field_name_for_filename].strip()}.html"
            filename = re.sub(r'[^\w\-_\. ]', '_', filename)  # Clean up the filename

            # Write the HTML to the file in the selected directory
            file_path = os.path.join(directory, filename)
            try:
                with open(file_path, "w", encoding="utf8") as f:
                    f.write(card_html)
            except Exception as e:
                errors.append(f"Error writing file {filename}: {str(e)}")

        # Show a dialog after all cards are processed
        if errors:
            utils.showInfo(f"Finished with errors:\n" + "\n".join(errors))
        else:
            utils.showInfo(f"All cards exported successfully to {directory}!")

    def process_media(self, text):
        # Handle both images and audio
        text = self.convert_images(text)
        text = self.convert_audio(text)
        return text

    def convert_images(self, text):
        collection_path = mw.col.media.dir()
        matches = re.findall(r'src="([^"]+)"', text)
        for match in matches:
            image_path = os.path.join(collection_path, match)
            if os.path.exists(image_path):
                with open(image_path, "rb") as img_file:
                    b64_string = base64.b64encode(img_file.read()).decode('ascii')
                    img_tag = f'data:image/jpeg;base64,{b64_string}'
                    text = text.replace(match, img_tag)
        return text

    def convert_audio(self, text):
        collection_path = mw.col.media.dir()
        matches = re.findall(r'\[sound:(.+?)\]', text)
        for idx, match in enumerate(matches):
            audio_path = os.path.join(collection_path, match)
            if os.path.exists(audio_path):
                with open(audio_path, "rb") as audio_file:
                    b64_string = base64.b64encode(audio_file.read()).decode('ascii')
                    audio_tag = f'''
                    <audio id="audio_{idx}" src="data:audio/mpeg;base64,{b64_string}" type="audio/mpeg"></audio>
                    <button class="audio-btn" onclick="playAudio('audio_{idx}')"></button>
                    '''
                    text = text.replace(f'[sound:{match}]', audio_tag)
        return text

# Add the action to Anki's menu
def show_export_dialog():
    dialog = ExportToHtmlDialog()
    dialog.exec()

action = QAction("Export Deck to HTML with Media", mw)
action.triggered.connect(show_export_dialog)
mw.form.menuTools.addAction(action)
