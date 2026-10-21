const express = require('express');
const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = 3000;

// Exécuter les scripts de synchronisation Python au démarrage
console.log("🔄 Lancement de la synchronisation de tous les flux...");
exec('python fetch_instagram.py && python fetch_all_feeds.py', (error, stdout, stderr) => {
  if (error) {
    console.error(`Erreur de synchronisation : ${error.message}`);
    return;
  }
  console.log(stdout);
});

// 1. Servir TOUS les fichiers statiques (images, CSS, JS frontend) depuis /public
app.use(express.static(path.join(__dirname, 'public')));

// 2. Routes API dédiées pour lire les JSON sans mettre tout le dossier racine en public
app.get('/instagram_data.json', (req, res) => {
  const filePath = path.join(__dirname, 'instagram_data.json');
  if (fs.existsSync(filePath)) {
    res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, private');
    res.sendFile(filePath);
  } else {
    res.status(404).json({ error: "Fichier non trouvé" });
  }
});

// Route générique pour tout autre fichier JSON éventuel à la racine (ex: youtube_data.json)
app.get('/:file.json', (req, res) => {
  const fileName = req.params.file + '.json';
  const filePath = path.join(__dirname, fileName);
  if (fs.existsSync(filePath)) {
    res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, private');
    res.sendFile(filePath);
  } else {
    res.status(404).send('Non trouvé');
  }
});

app.listen(PORT, () => {
  console.log(`🚀 Hub HugoDécrypte en ligne sur http://localhost:${PORT}`);
});
