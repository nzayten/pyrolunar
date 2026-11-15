// Downloads NASA PSI combustion investigations.
// USAGE: open https://psi.nasa.gov in a browser, press F12 > Console, paste this code and press Enter.
// Result: psi_combustion.json is downloaded (metadata + experimental tables/CSV for each investigation).

(async () => {
  // 1) Collect IDs (PSI-xx) of all "Combustion Science" investigations from the search API
  const ids = new Set();
  for (const term of ['combustion','flame','fire','smoke','droplet','soot','flammability','ACME','extinguishment','aerosol','dust','burning']) {
    for (let from = 0; from < 200; from += 25) {
      const r = await fetch(`/geode-py/ws/repo/search?term=${term}&source=psi&type=investigation&from=${from}&size=25`).then(r => r.json());
      const hits = r.hits.hits;
      hits.forEach(h => { if (String(h._source['Research Area']).includes('Combustion')) ids.add(h._source.Accession); });
      if (hits.length < 25) break;
    }
  }
  console.log('Investigations found:', ids.size);

  // 2) Download each investigation's metadata and experimental-table CSVs
  const recs = {};
  for (const id of ids) {
    const j = await fetch('/geode-py/ws/repo/investigations/' + id).then(r => r.json());
    const rec = {
      id, acronym: j.investigationAcronym, title: j.title, projectType: j.projectType, subArea: j.subResearchArea,
      platform: j.flightProgram, start: j.investigationStartDate, end: j.investigationEndDate, doi: j.doi,
      related: j.related_glds, hardware: j.experimentHardware, objective: j.objective, approach: j.approach,
      hypothesis: j.hypothesis, impacts: j.researchImpacts, sizeGB: +(Number(j.totalFileSize) / 1e9).toFixed(2),
      publications: (j.publications || []).map(p => ({ title: p.title, authors: p.authorList, doi: p.doi, year: p.year })),
      tables: []
    };
    for (const t of (j.experimentalTable || [])) {
      const r = await fetch(`/geode-py/ws/studies/${id}/download?file=${encodeURIComponent(t.file_name)}&version=${t.version}&redirect=false`);
      let txt = await r.text();
      if (txt.replace(/"/g, '').startsWith('http')) txt = await fetch(txt.replace(/"/g, '')).then(r => r.text());
      rec.tables.push({ file: t.file_name, csv: txt });
    }
    recs[id] = rec;
    console.log('Downloaded:', id, rec.acronym);
  }

  // 3) Save everything as one JSON file
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(recs)], { type: 'application/json' }));
  a.download = 'psi_combustion.json';
  a.click();
})();
