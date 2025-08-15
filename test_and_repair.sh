#!/bin/bash

# ==============================================================================
#  Professionelles Test- und Reparatur-Automatisierungs-Skript (Version 2)
# ==============================================================================

# --- Konfiguration ---
MAX_ATTEMPTS=5
PROJECT_SRC="." 

# --- Hilfsfunktionen für farbige Ausgaben ---
log_info() { echo -e "\033[1;34m[INFO]\033[0m $1"; }
log_success() { echo -e "\033[1;32m[SUCCESS]\033[0m $1"; }
log_warning() { echo -e "\033[1;33m[WARNING]\033[0m $1"; }
log_error() { echo -e "\033[1;31m[ERROR]\033[0m $1"; }
log_step() { echo -e "\n\033[1;36m--- $1 ---\033[0m"; }

# ==============================================================================
#  SCHRITT 0: Überprüfung der Werkzeuge (NEU & VERBESSERT)
# ==============================================================================
log_step "SCHRITT 0: Überprüfung der Werkzeug-Verfügbarkeit"

COMMANDS_TO_CHECK=("git" "pytest" "ruff") # 'black' wird durch 'ruff format' ersetzt
ALL_TOOLS_FOUND=true

for cmd in "${COMMANDS_TO_CHECK[@]}"; do
    if ! command -v $cmd &> /dev/null; then
        log_error "Werkzeug '$cmd' nicht gefunden. Bitte installieren Sie es."
        log_error "Für Python-Tools: pip install pytest pytest-cov ruff"
        ALL_TOOLS_FOUND=false
    fi
done

if ! $ALL_TOOLS_FOUND; then
    log_error "Nicht alle benötigten Werkzeuge sind installiert. Skript wird beendet."
    exit 1
else
    log_success "Alle Werkzeuge sind verfügbar."
fi


# ==============================================================================
#  SCHRITT 1: Sicherheitsüberprüfung des Git-Status
# ==============================================================================
log_step "SCHRITT 1: Sicherheitsüberprüfung des Git-Repositorys"

if ! git diff --quiet || ! git diff --cached --quiet; then
    log_error "Ihr Arbeitsverzeichnis ist nicht sauber. Bitte committen oder stashen Sie Ihre Änderungen."
    exit 1
else
    log_success "Git-Repository ist sauber. Der Prozess kann sicher gestartet werden."
fi

# ==============================================================================
#  SCHRITT 2: Start der Test-Analyse-Reparatur-Schleife
# ==============================================================================
attempt=1
while [ $attempt -le $MAX_ATTEMPTS ]; do
    log_step "VERSUCH $attempt von $MAX_ATTEMPTS"

    # --- Testphase ---
    log_info "Führe Tests aus und ermittle die Testabdeckung..."
    # Verbessert: Zeige Test-Output live an und logge ihn gleichzeitig
    pytest --cov=$PROJECT_SRC --cov-report=term-missing 2> pytest_errors.log | tee pytest_results.log
    TEST_EXIT_CODE=$?

    # --- Analysephase ---
    # Hinweis: Das Parsen der Textausgabe ist fragil. Für maximale Robustheit könnte man ein Plugin wie 'pytest-json-report' verwenden.
    COMPLETED_TESTS=$(grep -oP '(\d+ passed|\d+ failed)' pytest_results.log | sed 's/ passed//;s/ failed//' | awk '{s+=$1} END {print s+0}')
    FAILED_TESTS=$(grep -oP '\d+ failed' pytest_results.log | sed 's/ failed//' | awk '{s+=$1} END {print s+0}')
    COVERAGE=$(grep "TOTAL" pytest_results.log | awk '{print $NF}')

    log_info "Testergebnis-Zusammenfassung:"
    echo "  - Abgeschlossene Tests: ${COMPLETED_TESTS:-0}"
    echo "  - Fehlgeschlagene Tests: ${FAILED_TESTS:-0}"
    echo "  - Testabdeckung: ${COVERAGE:--}"

    if [ $TEST_EXIT_CODE -eq 0 ]; then
        log_success "Alle Tests wurden erfolgreich bestanden!"
        log_step "FINALE BERICHTE"
        cat pytest_results.log
        rm pytest_results.log pytest_errors.log
        exit 0
    else
        log_warning "Fehler in den Tests entdeckt. Starte Reparaturversuch..."
        log_info "Fehlerausgabe der Tests:"
        cat pytest_errors.log
    fi

    # --- Reparaturphase ---
    log_info "Reparaturphase 1: Führe automatische Formatierer und Linter aus..."
    # Modernisierter Ansatz: Ruff für Formatierung und Linting verwenden
    ruff format $PROJECT_SRC
    ruff check --fix $PROJECT_SRC

    # --- Reparaturphase 2: KI-gestützte Analyse (Implementiert) ---
    if git diff --quiet; then
        log_warning "Statische Tools konnten keine weiteren Fehler beheben."
        log_info "Reparaturphase 2: Generiere Prompt für KI-Analyse..."

        # Extrahiere die fehlerhaften Dateien aus der stderr-Ausgabe von pytest
        FAILING_FILES=$(grep -E "^===+ (FAILURES|ERRORS) ===+$" -A 1000 pytest_errors.log | grep -oP '^\S+\.py' | sort -u)

        if [ -n "$FAILING_FILES" ]; then
            PROMPT_FILE="ai_repair_prompt.txt"
            log_success "Generiere detaillierten Reparatur-Prompt in '$PROMPT_FILE'..."

            echo "Hello! I am running an automated test and repair script, and the static analysis tools could not fix the errors. Please analyze the following files and error logs and provide a patch to fix the issue." > "$PROMPT_FILE"
            echo -e "\n--- PYTEST ERROR LOG ---\n" >> "$PROMPT_FILE"
            cat pytest_errors.log >> "$PROMPT_FILE"

            for file in $FAILING_FILES; do
                echo -e "\n--- FILE CONTENT: $file ---\n" >> "$PROMPT_FILE"
                echo '```python' >> "$PROMPT_FILE"
                cat "$file" >> "$PROMPT_FILE"
                echo '```' >> "$PROMPT_FILE"
            done
            
            log_warning "Bitte kopieren Sie den Inhalt von '$PROMPT_FILE' und fügen Sie ihn in Ihren KI-Assistenten ein, um einen Reparaturvorschlag zu erhalten."
        else
            log_warning "Konnte keine spezifischen fehlerhaften Dateien aus dem Log extrahieren."
        fi
        log_error "Die KI-Reparatur erfordert manuelle Interaktion. Breche die Schleife ab."
        break # Verlasse die Schleife, da eine manuelle Aktion erforderlich ist.
    fi

    ((attempt++))
done

# ==============================================================================
#  SCHRITT 3: Endbewertung
# ==============================================================================
log_error "Maximale Anzahl von $MAX_ATTEMPTS Reparaturversuchen erreicht."
log_error "Die automatische Reparatur konnte nicht alle Fehler beheben."
log_info "Bitte analysieren Sie die letzte Fehlerausgabe und beheben Sie die Probleme manuell."
cat pytest_errors.log
rm pytest_results.log pytest_errors.log
exit 1