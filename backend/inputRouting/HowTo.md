# Run BON NDVI Prompt Workflow on Spark

Deze README is voor gebruikers die de bestaande workflow op Spark willen draaien.

De setup staat hier:

```bash
cd ~/naturedesk/uva-bon-project/backend/inputRouting

De workflow doet:

prompt -> Qwen via Ollama -> intent JSON -> BON input JSON -> BON run -> CSV/PNG results

1. Ga naar de juiste folder

cd ~/naturedesk/uva-bon-project/backend/inputRouting

2. Check of Qwen beschikbaar is

ollama list | grep qwen

Je moet iets zien zoals:

qwen2.5:7b

Als dit niets teruggeeft, is Qwen niet beschikbaar in Ollama.

3. Check of BON bereikbaar is

curl -I http://127.0.0.1:3001

Goed resultaat:

HTTP/1.1 200 OK

Als dit faalt, draait BON niet of zit je niet op de juiste machine/session.

4. Check of de BON template bestaat

ls -lh templates/bon_ndvi_template.json

Check of het geldige JSON is:

python3 -m json.tool templates/bon_ndvi_template.json > /tmp/template_check.json

Als dit een error geeft, is de template kapot.

5. Run de volledige workflow

Gebruik één command:

python3 run_workflow.py \
  "Run NDVI voor Zuid-Holland in groeiseizoen 2024 met median"

Dit start automatisch:

1. Prompt naar Qwen
2. Qwen output naar intent JSON
3. Intent JSON naar BON input JSON
4. BON pipeline run
5. Output folders ophalen
6. timeseries.csv downloaden
7. ndvi_timeseries.png downloaden

6. Waar staan de resultaten?

Elke run krijgt een eigen timestamp-folder onder runs/.

Bekijk de nieuwste run:

ls -lt runs | head

Voorbeeld:

20260610-174500

Ga naar die folder:

cd runs/20260610-174500

Daar staan:

prompt.txt
llm_config.json
bon_run_input.json
bon_run_response.txt
output_folders.json
timeseries.csv
ndvi_timeseries.png

7. Bekijk de resultaten

CSV bekijken:

head timeseries.csv

Run id bekijken:

cat bon_run_response.txt

Output folders bekijken:

cat output_folders.json

Plotbestand checken:

ls -lh ndvi_timeseries.png

8. Snel controleren of alles werkte

Vanaf inputRouting/:

LATEST=$(ls -td runs/*/ | head -1)
echo $LATEST
ls -lh "$LATEST"
head "$LATEST/timeseries.csv"

Als timeseries.csv en ndvi_timeseries.png bestaan, is de workflow succesvol uitgevoerd.

9. Andere prompt gebruiken

Voor Den Haag bijvoorbeeld:


python3 run_workflow.py \
  "Run NDVI voor Den Haag in groeiseizoen 2024 met median"

Let op: de huidige BON template is gebaseerd op Zuid-Holland. Voor een ander gebied moet ook de BON template/bbox aangepast zijn, anders blijft BON waarschijnlijk Zuid-Holland draaien.

10. Bekende beperking

De workflow downloadt automatisch:


timeseries.csv
ndvi_timeseries.png


De GeoTIFF wordt nog niet automatisch gedownload, omdat de exacte bestandsnaam/link voor de raster output nog uit BON gehaald moet worden.