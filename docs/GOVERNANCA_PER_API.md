### Gov Gen AI Platform · Governança per API

# Què comprova i registra la plataforma, i què d'això pot usar una aplicació feta fora

*Preparat el 2 de setembre de 2026 sobre el codi real del repositori, per a la reunió amb la Unitat d'Anàlisi i Desenvolupament TI. Complementa `docs/MARCO_GOBERNANZA_IA.md` (els principis, en castellà) i `docs/EVOLUCIO_I_ASPECTES_PENDENTS.md` (les qüestions obertes). L'estat de cada mecanisme és el del dia de la data.*

## 1. La posició, en quatre frases

La plataforma servix per a **tres coses**, i cap d'elles és «desenvolupar en lloc de desenvolupament»:

1. **Experimentar**: assajar un assistent o un informe amb IA sobre corpus real, amb escenaris, veredicte humà, dataset dorat i inspecció del prompt exacte, abans que ningú el done per bo.
2. **Fer executable el marc de governança**: les obligacions del Reglament d'IA, del RGPD, de la Llei 40/2015 i de l'ENS traduïdes a comprovacions que corren en cada petició i a registres que es generen per construcció (*compliance as code*). És el que descriu `MARCO_GOBERNANZA_IA.md`; ací es diu quines són i on estan.
3. **Governar el desenvolupament ciutadà** del nivell 2 de la Instrucció 02/2026: el registre, la revisió posterior i la caixa d'eines que la Instrucció encomana a la UADTI.

I la quarta frase és la que contesta l'objecció de desenvolupament: **una vegada els paràmetres de governança d'un cas d'ús estan definits i provats a la plataforma, la UADTI pot desenvolupar-lo fora**, amb les seues eines i el seu repositori, **sempre que l'aplicació registre per API a la plataforma** el que el marc exigix registrar, i use per API les comprovacions que no té sentit reimplementar. El nivell 3 de la Instrucció (desenvolupament corporatiu) pot viure dins de la plataforma o fora d'ella; el registre viu a un sol lloc.

El que la plataforma **no fa ni farà** (secció 3.1 del marc): l'inventari institucional de casos d'ús d'IA, la classificació de risc, la designació d'òrgan responsable o l'aprovació d'un cas d'ús nou. Són actes de govern, i un inventari que visca dins d'una de les eines que ha d'inventariar naix incomplet. La plataforma és on eixes decisions **es fan efectives i verificables**, no on es prenen.

## 2. Què hi ha hui per a una aplicació externa

Abans de l'inventari, el que ja pot fer una aplicació de la UADTI contra la plataforma, sense que ningú programe res més:

- **Autenticar-se amb un token personal (PAT)** amb permisos acotats. Catàleg vigent: `chatbots:read`, `chatbots:write` (només superadministrador), `redaccion:templates:read`, `redaccion:templates:write`, `chat:test`, `chat:debug` (veure el prompt final i la configuració resolta sense invocar el model) i `chat:onbehalf` (preguntar en nom d'una altra persona, el permís més sensible i per això separat).
- **Consumir un assistent de la plataforma des d'una interfície pròpia**: `POST /api/v1/hub/chat/{chatbot_id}` amb PAT o clau de widget, resposta en *streaming* amb fonts citables, avís de traducció i motiu si ha declinat. Cada resposta queda registrada a la plataforma amb la seua traça (§3), s'apliquen les quotes i la disponibilitat, i el contracte de cites i la porta de qualitat actuen igual que al widget. És a dir: **hui ja es pot construir una interfície pròpia sobre el motor i heretar tota la governança**.
- **Servidor MCP** (`mcp_server/`, transport stdio) per a agents: plantilles d'informe, xatbots i `test_chat`/depuració, amb el PAT de qui l'usa. Documentat a `docs/MCP_SERVER.md`.
- **Llegir els manifests d'execució** dels informes generats dins de la plataforma (`GET /api/v1/redaccion/...` de manifests), amb sessió.

## 3. Inventari: mecanisme, garantia, i accés des de fora

Llegenda de la columna «Des de fora»: **Hui** (existix una API o MCP), **REG.n / FUN.n** (planificat en eixe pas del pla), **Candidat** (no planificat; es proposa ací per a decidir-ho), **No** (no té sentit exposar-ho).

### 3.1 Registres que es generen per construcció

| Mecanisme | Què garantix | Norma | On viu | Des de fora |
| :---- | :---- | :---- | :---- | :---- |
| **Interacció + traça de diagnòstic** per resposta d'assistent: pregunta, resposta, tokens i cost, motiu de declinar, identificadors i notes de tot el que es va recuperar, configuració **per valor**, consulta reescrita o reformulada | Cada resposta és explicable mesos després; distingir un error de recuperació d'un de redacció; re-executar ablacions sense tornar a demanar treball humà | RIA art. 12 (registre d'esdeveniments) | `hub_interactions` + `interaction_metadata` (HIB.I); escrit per l'endpoint de xat | **Hui** per a qui consumix el xat per API (es registra sol). Per a un assistent construït fora: **REG.2** (esdeveniment de governança) |
| **Manifest d'execució d'un informe** (`DraftingRunManifest`, congelat): plantilla i versió, documents, validació d'entrada, blocs extrets, blocs d'IA amb model, versió de prompt i **abast del context**, cites, aprovacions humanes, blocs fallits, hash del document final, resum d'anonimització | Reproduïbilitat com a registre; res s'exporta sense manifest; s'emet també quan falla | RIA art. 12; Llei 40/2015 art. 41 | `hub_run_manifests`, `contracts/manifest.py` | Lectura: **Hui** (sessió). Que una aplicació externa **deposite** el seu manifest d'una generació feta fora: **Candidat** (§4.2) |
| **Registre d'aprovacions humanes** amb identitat, moment i versió aprovada; màquina d'estats de bloc amb esdeveniment d'auditoria per transició | Supervisió humana instrumentada, no ritual; cap bloc d'IA entra al document sense `approved` | RIA art. 14; RGPD art. 22 | `ApprovalRecord`, `BlockStateMachine` | Dins del manifest depositat: **Candidat** (§4.2) |
| **Registre d'activitat d'IA de governança** (`ActividadIAEvent`): actor, organització, eina externa, finalitat, model, categories de dades declarades; **metadades sí, contingut no**, per contracte | El registre que el RIA exigix al responsable del desplegament (arts. 12 i 26) i el que el registre d'activitats de tractament agraïx (RGPD art. 30), també per a l'IA que passa **fora** de la plataforma | RIA arts. 12 i 26; RGPD art. 30 | **Planificat**: bloc REG | **REG.2** (escriure, PAT amb `actividad:write`), **REG.4** (MCP remot), **REG.5** (llegir i exportar, acotat a l'organització) |
| **Escenaris de prova amb veredicte humà** i **revisió d'interaccions** (adequada, millorable, inadequada, fonts esperades, resposta de referència) | La mateixa consulta abans i després d'un canvi, amb qui la va jutjar i per què; el que cap mètrica substituïx en un assistent normatiu | RIA art. 9 (gestió de riscos), avaluació contínua del marc §5 | `hub_test_scenarios`, `hub_test_runs`, `hub_interactions.review_*` | Per a assistents de la plataforma: **Hui** (sessió). Per a un assistent extern: **Candidat** (§4.3, lligat a la decisió 8 de l'informe) |
| **Historial de configuració amb autoria**: prompts i nivell de model per activitat, versions de plantilla immutables, cascada Plataforma → Organització → Xatbot | Traçabilitat de la configuració que va regir cada execució | RIA art. 12 | `hub_activity_prompts`, `hub_prompt_templates`, versions de plantilla, `config_resolver` | Lectura dels paràmetres de governança efectius d'un cas d'ús: **Candidat** (§4.1) |
| **Traçat tècnic** per node i per crida al model (Langfuse) | Observabilitat token a token | Operació, no governança | `services/observability.py`, `graph/tracing.py` | **No**: és observabilitat; una aplicació externa té el seu propi traçat. El registre de governança (REG) és el punt comú |

### 3.2 Comprovacions que corren en cada petició

| Mecanisme | Què garantix | Norma | On viu | Des de fora |
| :---- | :---- | :---- | :---- | :---- |
| **Contracte de cites**: una resposta que no cite cap URL de l'evidència recuperada (o cap document que l'agent haja llegit de veritat) se substituïx pel missatge de «no ho sé», amb el motiu registrat | El sistema no emet una afirmació que no puga fonamentar; determinista, no una instrucció al model | RIA art. 13; dret a la bona administració | `agent/citation_validator.py`, aplicat pel `CoreGraph` | Dins del xat per API: **Hui**. Com a servici per a respostes generades fora (`text + fonts permeses → veredicte i cites vàlides`): **VAS.1** (planificat, §4.4) |
| **Porta de qualitat**: similitud del millor fragment contra un llindar per cas d'ús, amb una reformulació i només una | Declinar quan el corpus no dóna fonament, amb llindar mesurat per assistent | RIA art. 9 | `core_graph.py` (`merge`, `quality_gate`) | Dins del xat per API: **Hui**. Fora: **No** (depén del corpus i de l'embedding de la plataforma) |
| **Comprovació de fonament** amb model jutge | Detectar afirmacions no sostingudes per les fonts | RIA art. 13 | `agent/grounding_check.py` | **Apagada per mesura** (rebutjava 10 de 30 respostes bones); no s'exposa mentre no millore |
| **Avís de vigència**: una norma sense validació humana de vigència es cita amb avís afegit **després** de generar, no pel prompt | No afirmar com a vigent el que ningú ha comprovat | RIA art. 10; bona administració | `services/retrieval/vigencia.py` | Dins del xat: **Hui**. Consulta de l'estat de vigència d'un document del corpus per a citar-lo des de fora: **VAS.2** (planificat, §4.5) |
| **Filtre de metadades en SQL** abans del `LIMIT`: públic, no substituït, apte per a assistents, **una versió per norma segons la llengua**, normes no vigents excloses; eixamplar el tema no eixampla el permís | Un document exclòs no consumix plaça ni es filtra «després» | RIA art. 10; ENS | `services/retrieval/metadata_filter.py`, `retriever.py` | Dins del xat: **Hui**. Fora: **No** (és intern al recuperador) |
| **Detecció de dades personals i anonimització** en quatre modes (desactivat, detecció, substitució reversible, emmascarat irreversible), aplicada **abans** del model i revertida després; el mapa no ix del node | Minimització i seudonimització; categories especials sempre irreversibles | RGPD arts. 5.1.c, 25 i 9; LOPDGDD DA 7a | `modules/redaccion/services/anonymization/` | **REG.3**: `POST /anonimizacion/spans` i `/replace` amb PAT `anonimizacion:use`; el text no toca ni logs ni base de dades, amb test |
| **Auditoria estàtica del codi** en tres nivells (segura, avís, crítica): `eval`, introspecció de l'intèrpret, rutes absolutes, mòduls fora de la llista, codi que no compila; i **sandbox** en xarxa aïllada, sense privilegis, subprocés efímer, re-auditoria dins | Cap codi d'usuari ni generat corre al procés del servidor; l'accés al sistema operatiu és una capacitat, no un forat | ENS; Instrucció 02/2026 regla 1 i Annex III.3 del Reglament d'IA de la UJI | `services/script_auditor.py`, `core/sandbox_client.py`, `docs/SANDBOX_SECURITY.md` | Executar una funció del catàleg des de fora: **FUN.6** (PAT `funciones:execute`, esdeveniment REG). **Auditar un script que corre fora** (la revisió posterior del nivell 2 com a servici): **VAS.3** (planificat, §4.6), amb la caixa d'eines publicada des del codi |
| **Contracte d'entrada validat abans d'executar**: una funció declara ranures de fitxer i paràmetres tipats; una entrada que no complix falla amb un error llegible sense tocar el sandbox | Cap traça de pandas per un ERP que canvia de format; el formulari ix del contracte | Determinisme primer (P1), transparència (P5) | Planificat: FUN.2 | **FUN.6** (l'API valida igual) |
| **Quotes en cascada** (usuari/dia i mes, xatbot/dia, organització/mes, IP anònima/dia), comprovades abans del model i comptabilitzades després; **disponibilitat** per dates i pressupost, calculada i no guardada | Frugalitat i control del gasto; un assistent de campanya caduca sol | Frugalitat (P2) | `core/quotas.py`, `core/chatbot_availability.py` | Dins del xat: **Hui**. Fora: **No** (governen recursos de la plataforma) |
| **Frontera de dades i d'aplicació**: dues bases declaratives (configuració sincronitzable / operacional només edge), classificació de cada router, prohibició d'imports edge→cloud vigilada per tests | Localització del dada: el que no ix del perímetre no es pot fugar | Sobirania (P8); ENS | `database/base.py`, `main.py`, guardarraïls en `tests/` | **No** aplica: és arquitectura. Però determina que **tot el que registra dades del client és edge**, també el que arriba per API |
| **Accés per organització**: acotació de llistats i 403 en dues capes (qui pot veure què; quina fila guanya) | Separació entre organitzacions provada sobre base real | RGPD; ENS | `core/auth/tenancy.py`, `core/ambito.py` | Dins de totes les API: **Hui** (l'organització es deriva del token, mai del cos de la petició) |

### 3.3 Qualitat de la informació que consumix la IA

| Mecanisme | Què garantix | Norma | On viu | Des de fora |
| :---- | :---- | :---- | :---- | :---- |
| **Curació**: rastreig de portals, detectors deterministes i semàntics de patologies (buit, il·legible, duplicat, obsolet, contradictori), exclusió registrada, caducitat activa, detecció de forats a partir de consultes no fonamentades i de valoracions negatives | Al corpus només entra el que ha passat el contracte de format i la revisió; una resposta correcta sobre una norma derogada és un dany | RIA art. 10 | `modules/curation/`, `docs/CONTRATO_MD_CORPUS.md` | **No** com a servici. Els informes de qualitat del corpus són evidència per al pla institucional (marc §5) |
| **Vocabulari com a dada** i **taxonomia fora del text embegut**: reclassificar costa un `UPDATE` | La classificació es pot revisar de veritat, perquè revisar-la no costa un reindexat | Gestió de riscos (P9) | `hub_vocabulary_terms`, regla d'`embedding_text` | **No** aplica fora |
| **Dataset dorat amb empremta del corpus** com a porta d'integració contínua, i CLI nocturna contra el corpus real | Cap canvi del recuperador s'adopta si degrada la recuperació respecte de la línia base | Avaluació contínua (marc §5) | `evaluation/golden_dataset.py`, `run_golden.py`, test de porta | Per a assistents de la plataforma: **Hui** (CLI). Fora: **Candidat** només si hi ha assistents externs registrats (§4.3) |

## 4. Els candidats: què caldria exposar perquè la UADTI desenvolupe fora amb registre dins

Són el que falta per a la frase quarta de §1, amb un cost orientatiu (no mesurat). **Tots van després del bloc REG**, que construïx el token de màquina amb permisos, l'esdeveniment de governança i el MCP remot que tots reutilitzen. **Tres ja estan planificats** com a bloc VAS del pla (§4.4, §4.5 i §4.6: els de cost baix que ja existixen com a funció i només necessiten superfície; quatre passos, després de REG). Els altres tres (§4.1, §4.2, §4.3) **no**, i esperen a la primera aplicació externa real que els necessite.

### 4.1 Lectura dels paràmetres de governança d'un cas d'ús

`GET /api/v1/governanca/casos-d-us/{id}/parametres`: nivell de model assignat per activitat, mode de disociació exigit, on hi ha portes de revisió humana, llindar de qualitat, llengua, categories de dades declarades. És «una vegada definits els paràmetres» fet literal: la UADTI llig de la plataforma **la configuració que el pla institucional ha decidit** per a eixe cas d'ús i la seua aplicació la respecta. Hui eixa configuració existix per xatbot i per plantilla; el que faltaria és el concepte de «cas d'ús» que abrace un assistent construït fora. **Cost baix** si es modela com un xatbot de tipus `extern` (§4.3); alt si es crea una entitat nova.

### 4.2 Depòsit del manifest d'una execució feta fora

`POST /api/v1/governanca/manifests` amb el mateix contracte que `DraftingRunManifest` (o el subconjunt que apliqui a un assistent: model, versió de prompt, fonts citades, aprovacions humanes, hash de la sortida), validat amb `extra="forbid"` i **sense contingut**. És el pas de l'esdeveniment de governança (REG.2, «qui, què, quan, amb quina finalitat») a l'evidència per execució (RIA art. 12 en el sentit fort). Una aplicació de la UADTI que genere informes amb IA depositaria el manifest de cada generació, i el panell els mostraria al costat dels de la plataforma. **Cost mitjà**: el contracte existix; falta el contenidor genèric i la lectura.

### 4.3 Assistents externs registrats, amb escenaris i veredicte

Registrar un xatbot de tipus `extern` amb un *endpoint* de la UADTI: la plataforma no el servix, però **li passa els escenaris de prova**, registra les respostes com a execucions amb veredicte, i pot aplicar-li el contracte de cites (§4.4) contra el corpus si el corpus és el de la plataforma. És la variant (b) de la decisió 8 de l'informe («agents remots orquestrats») mirada des de la governança i no des de l'extensió: el graf no delega la generació, sinó que **l'avalua**. **Cost mitjà**. És el candidat que més directament contesta «nosaltres podem fer els xatbots»: sí, i la plataforma els assaja i els registra igual que als seus.

### 4.4 El contracte de cites com a servici (planificat: VAS.1)

`POST /api/v1/verificacions/cites` amb `{text, fonts_permeses}` → `{compleix, cites_valides, cites_invalides}`. És determinista, no toca el model i ja existix com a funció; exposar-lo costa un router i els tests. **Cost baix**. Permet que un assistent fet fora aplique la mateixa regla de «cap afirmació sense font resoluble» i que el resultat quede registrat.

### 4.5 Estat de vigència d'un document del corpus (planificat: VAS.2)

`GET /api/v1/corpus/documents/{id}/vigencia`: validada o no, per qui, quan, i el text de l'avís que la plataforma afegiria. Perquè una aplicació externa que cite normativa del mateix corpus no afirme com a vigent el que la plataforma avisaria. **Cost baix**; la dada existix a `hub_documents`.

### 4.6 L'auditoria estàtica com a servici (la revisió posterior del nivell 2 per a codi que corre fora; planificat: VAS.3)

`POST /api/v1/verificacions/codi` amb un script → resultat en tres nivells amb línia i regla de cada troballa, més el veredicte de si pot passar a revisió humana. La Instrucció (§8.4) diu que la UADTI revisa a posteriori «recolzant-se en eines d'IA i en l'anàlisi estàtica». L'auditor ja és exactament això, i **les seues regles són la caixa d'eines** de la regla 1: si la UADTI les manté, tindre-les com a servici fa que un script de nivell 2 que **no** vaja a córrer a la plataforma (per exemple una automatització local del servici) passe igualment per la mateixa vara. **Cost baix**. És el candidat que millor encaixa amb el paper que la Instrucció dóna a la UADTI, i per això convindria que fóra la UADTI qui diguera si el vol.

## 5. El que això demana de la UADTI, dit sense rodeos

- **Definir la caixa d'eines** (regla 1 de la Instrucció): mantindre les regles de l'auditor estàtic i contrastar-les amb les Guies Operatives Tècniques. Hui les mantenim nosaltres, i és un paper que no ens correspon.
- **Assumir la cua de revisió posterior** del catàleg de funcions (nivell 2), amb el mostreig i la suspensió, que és literalment el que la Instrucció (§9) li encomana.
- **Decidir, amb l'OIATI, el règim d'execució**: la Instrucció parla d'execució local amb credencials pròpies; la plataforma executa al node institucional vora les dades. És més controlat, però és distint, i que ho siga és una decisió seua.
- **Registrar per API** el que desenvolupe fora: l'esdeveniment de governança (REG.2) com a mínim, i el manifest (§4.2) quan hi haja generació d'informes amb IA.
- **Triar entre els sis candidats** de §4, o cap: la plataforma ja funciona sense ells; el que no funciona sense ells és un registre únic de l'activitat amb IA de la institució quan part d'eixa activitat es construïx fora.

## 6. Documents relacionats

- `docs/MARCO_GOBERNANZA_IA.md`: els principis P1–P11 i la taula d'evidència (§5), en castellà.
- `docs/EVOLUCIO_I_ASPECTES_PENDENTS.md`: les qüestions per a la reunió, en valencià; la Qüestió 7 resumix este document.
- `docs/SANDBOX_SECURITY.md`: el model d'amenaces de l'execució de codi.
- `docs/MCP_SERVER.md`: el servidor MCP i el mapa de permisos a eines.
- `planificacion/Plan_TDD_Fase1.md` §Bloque REG i §Bloque FUN: el que està planificat de la taula.
- `_local/Instruccio_02_2026_Desenvolupament_Ciutada_Governat (2).md`: la Instrucció (fora del repositori).
