README - BON NEO SignalEyes / Boombasis workflow

Deze README beschrijft hoe je de NEO SignalEyes / Boombasis workflow via BON in a Box draait, welke bestanden worden aangemaakt, hoe je de resultaten veilig kunt interpreteren, hoe je ze aan een ander model kunt geven voor reasoning, en welke bekende problemen kunnen optreden.

Doel van deze workflow

De workflow haalt NEO SignalEyes / Boombasis boomdata op via BON in a Box. De belangrijkste entities zijn:

• crown: boomkroon-polygonen
• centerpoint: boom- of object-centerpoints

De output is bedoeld als gelicentieerde comparator, benchmark of referentielaag voor de challenge. Gebruik deze output niet als ground truth, officiële Groenmonitor-validatie, gemeentelijke goedkeuring, of bewijs dat NatureDesk Crown Volume gevalideerd is.

Veilige wording:

• NEO benchmark/reference layer
• licensed comparator
• operational benchmark
• reference dataset under licence

Niet gebruiken:

• ground truth
• validation proof
• official Groenmonitor equivalence
• municipal validation
• NatureDesk Crown Volume is validated

Belangrijke rechten- en veiligheidsgrenzen

NEO credentials mogen nooit in prompts, README’s, logs, Git commits, screenshots of chat worden gezet.

De NEO data mag alleen binnen de afgesproken non-commercial/no-fee challenge-context worden gebruikt.

Raw NEO GeoJSON of full-city data niet zomaar uploaden naar externe LLMs of externe tooling. Voor reasoning met een model: gebruik bij voorkeur samenvattingen, counts, schema’s en kleine preview-fragmenten. Gebruik een lokaal model als je met raw GeoJSON wilt experimenteren.

Waar staat de workflow?

De student-wrapper staat hier:

~/naturedesk/uva-bon-project/backend/inputRouting

Belangrijke file:

neo_workflow.py

Deze doet:

prompt naar Qwen via Ollama -> NEO intent JSON -> BON input JSON -> BON run -> outputbestanden downloaden naar een timestamp-runfolder.

BON pipeline-bestanden staan aan de BON-kant:

/home/hans/.openclaw/workspace/bon-in-a-box-pipelines/pipelines/Netherlands_neo_signaleyes_boombasis_pipeline_41.json

/home/hans/.openclaw/workspace/bon-in-a-box-pipelines/scripts/data/queryNeoSignalEyes.py

/home/hans/.openclaw/workspace/bon-in-a-box-pipelines/scripts/data/queryNeoSignalEyes.yml

Basisrun

Ga naar de wrapper folder:

cd ~/naturedesk/uva-bon-project/backend/inputRouting

Run een kleine smoke test:

python3 neo_workflow.py "Run een NEO smoke test voor Den Haag met crown en centerpoint"

Verwachte intent in llm_config.json:

pipeline: neo
mode: tiny_aoi
entities: crown en centerpoint
max_pages: 1
admin_unit_level: wijk
admin_unit_preset: all_wijken
metric_theme: all_metric_themes

Belangrijk: tiny_aoi is alleen een technische smoke test. Gebruik deze niet om conclusies over heel Den Haag te trekken.

Modes

metadata

Haalt metadata/schema-informatie op. Geen echte feature-AOI capture. Gebruik dit om te checken of de API en entity metadata bereikbaar zijn.

tiny_aoi

Haalt een kleine test-AOI in Den Haag op. Dit is de juiste eerste test om te controleren of credentials, BON, outputrouting en GeoJSON preview werken.

full_city

Haalt de volledige GM0518 Den Haag AOI op. Dit is een grote capture en kan lang duren. Niet gebruiken als snelle smoke test.

Admin selectors

admin_unit_level en admin_unit_preset worden op dit moment vooral als context/provenance opgeslagen. Ze veranderen nog niet automatisch de echte NEO AOI.

Dus:

• full_city is echt GM0518 Den Haag
• tiny_aoi is echt klein
• stadsdeel/wijk/buurt zijn nu contextlabels, geen echte spatial subset

Voor echte stadsdeel-, wijk- of buurt-AOI’s moet de pipeline later worden uitgebreid zodat admin_unit_preset ook een boundary selecteert en als AOI naar NEO stuurt.

Edgecase-runs

Aanbevolen volgorde:

1. metadata crown + centerpoint
2. tiny_aoi crown + centerpoint
3. tiny_aoi crown only
4. tiny_aoi centerpoint only
5. context stadsdeel/wijk/buurt met tiny_aoi
6. full_city met max_pages 5 of 25 als beperkte test
7. full_city zonder max_pages pas als laatste

Voorbeelden:

python3 neo_workflow.py --runs-dir runs/neo_edgecases "Run NEO metadata only voor crown en centerpoint"

python3 neo_workflow.py --runs-dir runs/neo_edgecases "Run een NEO tiny AOI smoke test voor Den Haag met crown en centerpoint, max pages 1"

python3 neo_workflow.py --runs-dir runs/neo_edgecases "Run NEO tiny AOI voor Den Haag met alleen crown, max pages 1"

python3 neo_workflow.py --runs-dir runs/neo_edgecases "Run NEO tiny AOI voor Den Haag met alleen centerpoint, max pages 1"

python3 neo_workflow.py --runs-dir runs/neo_edgecases "Run NEO voor context stadsdeel Centrum SD05 met crown en centerpoint, gebruik tiny_aoi en max pages 1"

python3 neo_workflow.py --runs-dir runs/neo_edgecases "Run NEO voor context wijk Scheveningen WK051807 met crown en centerpoint, gebruik tiny_aoi en max pages 1"

python3 neo_workflow.py --runs-dir runs/neo_edgecases "Run NEO voor context buurt Belgisch Park BU05180271 met crown en centerpoint, gebruik tiny_aoi en max pages 1"

python3 neo_workflow.py --runs-dir runs/neo_edgecases "Run NEO full city GM0518 Den Haag met crown en centerpoint"

Outputlocaties

Er zijn drie relevante locaties.

A. Student wrapper runfolder

Voorbeeld:

~/naturedesk/uva-bon-project/backend/inputRouting/runs/20260616-171451

Of bij edgecases:

~/naturedesk/uva-bon-project/backend/inputRouting/runs/neo_edgecases/20260616-171451

Deze map bevat de prompt, Qwen intent, BON input, run id, output_folders en gedownloade kopieën van de belangrijkste outputbestanden.

Dit is meestal de map die je bekijkt voor debugging, demo en verdere analyse.

B. Echte BON outputfolder

output_folders.json bevat een relatieve BON outputmap, bijvoorbeeld:

data/queryNeoSignalEyes/G7fhk1lAMXbujDoVkz_XgEUc-kE5

Op de machine staat dit ongeveer onder:

/home/hans/.openclaw/workspace/bon-in-a-box-pipelines/output/data/queryNeoSignalEyes/G7fhk1lAMXbujDoVkz_XgEUc-kE5

Via BON/nginx is dit bereikbaar als:

http://127.0.0.1:3001/output/data/queryNeoSignalEyes/G7fhk1lAMXbujDoVkz_XgEUc-kE5/...

C. Controlled NEO source root

De NEO scriptlaag schrijft raw/source-capture materiaal naar:

/sources/commercial_internal/neo_signaleyes/den_haag_2026-06-15

Deze locatie is bedoeld voor gecontroleerde broncapture, provenance, raw pages en checksums. Niet behandelen als gewone losse student-output om zomaar te verspreiden.

Bestanden in de wrapper runfolder

prompt.txt

De oorspronkelijke prompt waarmee de run gestart is.

llm_config.json

De intent die Qwen heeft gemaakt. Dit is een compacte, menselijke configuratie. Gebruik dit om te controleren of Qwen de juiste mode, entities en context heeft gekozen.

bon_run_input.json

De exacte input die naar BON is gestuurd. Dit gebruikt BON-interne keys zoals:

• data>queryNeoSignalEyes.yml@0|mode
• data>queryNeoSignalEyes.yml@0|entities
• data>queryNeoSignalEyes.yml@0|max_pages

Gebruik dit bestand voor technische debugging.

bon_run_response.txt

De BON run-id. Voorbeeldvorm:

Netherlands_neo_signaleyes_boombasis_pipeline_41>...

output_folders.json

De outputfolder(s) die BON voor de run heeft aangemaakt. Als dit bestand een error-veld bevat, is de BON-stap niet volledig geslaagd. Als er geen error-veld staat, is de BON-stap technisch geslaagd.

neo_signaleyes_pipeline41_summary.json

De hoofd-samenvatting van de run. Begin meestal hier.

Dit bestand verwijst naar mode, entities, output root, provenance, checksums en counts.

neo_signaleyes_pipeline41_metadata_provenance.json

Provenance voor metadata mode.

neo_signaleyes_pipeline41_tiny_aoi_provenance.json

Provenance voor tiny_aoi mode.

neo_signaleyes_pipeline41_full_city_provenance.json

Provenance voor full_city mode, zodra de full-city run klaar is.
Provenance-bestanden beschrijven bron, pipeline-id, gebruikte mode, requestparameters zonder credentials, AOI-informatie, hashes, boundaries en non-claims.

neo_signaleyes_pipeline41_metadata_counts.json
Counts-sidecar voor metadata mode. Metadata mode heeft meestal geen echte feature counts zoals tiny_aoi of full_city.

neo_signaleyes_pipeline41_tiny_aoi_counts.json

Compact telbestand per entity voor tiny_aoi. Hierin staan onder andere:

• entity
• mode
• geo_type
• total_pages_reported
• pages_retrieved
• feature_count
• schema_path

neo_signaleyes_pipeline41_full_city_counts.json

Compact telbestand per entity voor full_city, zodra de full-city run klaar is.

neo_signaleyes_pipeline41_metadata_checksums.sha256

Checksum manifest voor metadata mode.

neo_signaleyes_pipeline41_tiny_aoi_checksums.sha256

Checksum manifest voor tiny_aoi mode.

neo_signaleyes_pipeline41_full_city_checksums.sha256

Checksum manifest voor full_city mode.

neo_signaleyes_pipeline41_crown_map_preview.geojson

GeoJSON previewlaag voor crown polygonen. Dit is het belangrijkste kaartbestand voor boomkroon-geometrieën.

Bij een crown-only run bestaat deze wel. Bij een centerpoint-only run kan deze ontbreken. Dat is normaal.

neo_signaleyes_pipeline41_centerpoint_map_preview.geojson

GeoJSON previewlaag voor centerpoints. Dit is het belangrijkste kaartbestand voor boompunten/objectpunten.

Bij een centerpoint-only run bestaat deze wel. Bij een crown-only run kan deze ontbreken. Dat is normaal.

Wanneer is een run geslaagd?

Een metadata run is geslaagd als:

• output_folders.json geen error bevat
• summary bestaat
• metadata provenance bestaat
• metadata checksums bestaan

Een tiny_aoi run is geslaagd als:

• output_folders.json geen error bevat
• summary bestaat
• tiny_aoi counts bestaat
• tiny_aoi provenance bestaat
• minstens de gevraagde GeoJSON preview bestaat

Een crown-only run is geslaagd als crown preview bestaat. Het ontbreken van centerpoint preview is dan normaal.

Een centerpoint-only run is geslaagd als centerpoint preview bestaat. Het ontbreken van crown preview is dan normaal.

Een full_city run is geslaagd als:

• output_folders.json geen error bevat
• later summary/provenance/counts/checksums verschijnen
• de raw pages in de controlled source root zijn geschreven
• de wrapper de outputbestanden kan downloaden of je ze later handmatig kunt bereiken

Full-city duurt langer

full_city zonder max_pages is een echte grote capture. Dit is geen snelle smoke test.

BON kan al een outputfolder teruggeven terwijl het script nog raw pages schrijft. In dat geval bestaat neo_signaleyes_pipeline41_summary.json nog niet en krijg je tijdelijk 404 bij downloaden.

Dat betekent niet meteen dat de run gefaald heeft.

Monitor full_city met:

curl -I http://127.0.0.1:3001/output/data/queryNeoSignalEyes/OUTPUT_FOLDER_ID/neo_signaleyes_pipeline41_summary.json

Zolang dit 404 geeft, is de summary nog niet klaar. Als dit 200 OK geeft, kun je de output downloaden.

De wrapper-download retry moet voor full_city langer zijn dan voor tiny_aoi. Gebruik bijvoorbeeld attempts 240 en delay_seconds 15 in de download functie. Dat wacht maximaal ongeveer een uur.

Bekende problemen en oplossingen

Probleem: run_workflow.py draait nog NDVI

Symptomen:

• Prompt -> intent JSON
• pipeline: ndvi
• Run id begint met ndvi_pipeline
• error over NDVI output folder

Oplossing:

Gebruik neo_workflow.py, of vervang run_workflow.py door de NEO-versie.

Probleem: Qwen mist admin_unit_level, admin_unit_preset of metric_theme

Symptoom:

Missing config keys: admin_unit_level, admin_unit_preset, metric_theme

Oplossing:

Gebruik apply_defaults in neo_workflow.py voordat validate_intent wordt aangeroepen. Defaults zijn:

• admin_unit_level: wijk
• admin_unit_preset: all_wijken
• metric_theme: all_metric_themes

Probleem: max_pages geeft BON 500

Symptoom:

Constant data>queryNeoSignalEyes.yml@0|max_pages has no value in JSON file

Oorzaak:
max_pages stond eerst als options-input met numerieke waarden. BON kon dat niet goed verwerken.

Oplossing:
De BON pipeline-definitie is aangepast: max_pages is nu type int. De wrapper moet max_pages als nummer sturen, bijvoorbeeld 1, niet als string "1".

Probleem: output_folders.json bevat error over string not in options

Symptoom:

Received value 1 as String not in options

Oorzaak:

Wrapper stuurde max_pages als string nadat de pipeline nog options verwachtte.

Oplossing:

Gebruik de huidige pipeline-definitie met max_pages type int en stuur max_pages als nummer.

Probleem: download geeft 404 direct na BON run

Symptoom:

Download failed ... HTTP 404 Not Found

Oorzaak:

BON heeft de outputfolder al gemeld, maar nginx/static serving of het script heeft het bestand nog niet klaar.

Oplossing:

Retry downloads. Voor tiny_aoi zijn korte retries genoeg. Voor full_city zijn langere retries nodig.

Probleem: missing optional map preview bij crown-only of centerpoint-only

Symptoom:

Skipped missing optional output voor centerpoint_map_preview bij crown-only, of crown_map_preview bij centerpoint-only.

Oorzaak:

Je hebt maar één entity gevraagd. De andere preview bestaat dan terecht niet.

Oplossing:

Geen probleem. Dit is verwacht gedrag.

Probleem: stadsdeel/wijk/buurt lijkt geen andere kaart te geven

Oorzaak:

admin_unit_level en admin_unit_preset zijn nu context/provenance, geen echte AOI selector.

Oplossing:

Voor echte stadsdeel/wijk/buurt runs moet de pipeline uitgebreid worden met boundary-selectie en AOI WKT generatie per admin unit.

Resultaten gebruiken voor een ander model

Gebruik bij voorkeur deze bestanden als modelcontext:

1. neo_signaleyes_pipeline41_summary.json
2. neo_signaleyes_pipeline41_*_counts.json
3. neo_signaleyes_pipeline41_*_provenance.json
4. llm_config.json
5. bon_run_input.json
6. eventueel een klein fragment uit crown_map_preview.geojson of centerpoint_map_preview.geojson

Geef een ander model niet meteen de volledige raw full-city GeoJSON, zeker niet als dat model extern draait. Gebruik eerst counts, schema’s en provenance.

Veilige modelvraag voor tiny_aoi:

Analyseer deze NEO Pipeline 41 tiny_aoi run als technische smoke test. Gebruik summary, counts en provenance. Trek alleen conclusies over pipelinewerking, outputbeschikbaarheid, schema en bruikbaarheid als preview. Trek geen conclusies over heel Den Haag en noem NEO niet ground truth.

Veilige modelvraag voor full_city:

Analyseer deze NEO Pipeline 41 full_city GM0518 run als licensed comparator/reference layer. Gebruik counts, provenance en schema. Beschrijf feature counts, beschikbare velden, outputdekking en mogelijke vervolganalyse. Maak geen officiële validatieclaim, geen ground-truth claim en geen claim dat NatureDesk Crown Volume gevalideerd is.

Aanbevolen extra afgeleide bestanden

Je kunt later een analyse-script toevoegen dat in dezelfde runfolder schrijft:

neo_metrics.json

Bevat compacte metrics zoals:

• run_mode
• entities
• crown_feature_count
• centerpoint_feature_count
• pages_retrieved
• total_pages_reported
• property_keys
• geometry_types
• available_height_fields
• available_area_fields

neo_conclusion.md

Bevat een korte, veilige conclusie op basis van summary, counts en provenance.

Voor tiny_aoi moet de conclusie technisch blijven.

Voor full_city mag de conclusie beschrijven wat is opgehaald en welke benchmarkanalyse mogelijk is, maar niet claimen dat iets officieel gevalideerd is.

Voorbeeld tiny_aoi conclusie

NEO Pipeline 41 tiny_aoi smoke test is technisch geslaagd. De run haalde NEO crown en/of centerpoint data op, schreef summary, counts, provenance en checksums, en maakte GeoJSON previewlagen voor de gevraagde entities. Deze output toont dat BON, NEO retrieval, outputrouting en previewdownload werken. Omdat de run tiny_aoi gebruikt, is deze output niet representatief voor heel Den Haag en mag hieruit geen gemeente-brede boomconclusie worden getrokken.

Voorbeeld full_city conclusie
NEO Pipeline 41 full_city GM0518 run heeft NEO crown en centerpoint data voor Den Haag opgehaald als licensed comparator/reference layer. De output kan worden gebruikt voor feature counts, schema-inspectie, kaartpreview en voorbereiding van vergelijking met NatureDesk Crown Volume proxy’s. Deze output ondersteunt benchmark- en referentieanalyse, maar is geen automatische validatie, officiële Groenmonitor-equivalentie of ground-truth claim.

Praktische aanbevolen workflow

1. Run metadata.
2. Run tiny_aoi crown + centerpoint.
3. Controleer counts en GeoJSON previews.
4. Run crown-only en centerpoint-only edgecases.
5. Run contextlabels voor stadsdeel/wijk/buurt als provenance-test.
6. Run full_city eerst met max_pages 5 of 25 als beperkte test.
7. Run full_city zonder cap alleen als je tijd hebt en de outputroot voldoende ruimte heeft.
8. Laat full_city doorlopen; niet opnieuw starten als hij nog raw pages schrijft.
9. Maak daarna neo_metrics.json en neo_conclusion.md als afgeleide analysebestanden.
10. Houd brondata/provenance en interpretatie gescheiden.

Korte samenvatting

Voor demo/debugging gebruik je vooral de wrapper runfolder.

Voor BON interne output kijk je in de BON outputfolder.

Voor controlled raw capture kijk je in de NEO source root.

Tiny AOI bewijst dat de workflow technisch werkt.

Full city is de echte grote Den Haag capture.

Stadsdeel/wijk/buurt zijn nu nog contextlabels, geen echte AOI-subsets.

Gebruik NEO als licensed comparator/reference layer, niet als ground truth of officiële validatie.