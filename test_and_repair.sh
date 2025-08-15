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
COMMANDS_TO_CHECK=("git" "pytest" "black" "ruff")
ALL_TOOLS_FOUND=true

for cmd in "${COMMANDS_TO_CHECK[@]}"; do
    if ! command -v $cmd &> /dev/null; then
        log_error "Werkzeug '$cmd' nicht gefunden. Bitte installieren Sie es."
        log_error "Für Python-Tools: pip install pytest pytest-cov black ruff"
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
    pytest --cov=$PROJECT_SRC > pytest_results.log 2> pytest_errors.log
    TEST_EXIT_CODE=$?

    # --- Analysephase ---
    # Diese Befehle wurden robuster gemacht für den Fall, dass die Log-Datei leer ist.
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
    black $PROJECT_SRC
    # KORRIGIERTER BEFEHL für Ruff
    ruff check --fix $PROJECT_SRC

    # --- Phase 2 (Simulation) ---
    if git diff --quiet; then
        log_warning "Statische Tools konnten keine weiteren Fehler beheben."
        log_info "Reparaturphase 2: KI-gestützte Analyse (Simulation)..."
        log_warning "KI-Reparatur ist in diesem Skript simuliert und wird übersprungen."
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