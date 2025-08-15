#!/bin/bash

# ==============================================================================
#  Professionelles Test- und Reparatur-Automatisierungs-Skript
# ==============================================================================
#
#  Dieses Skript implementiert eine "Test-Analyse-Reparatur"-Schleife.
#  Es führt Tests aus, analysiert Fehler, wendet automatische Korrekturen an
#  und wiederholt den Vorgang, bis alle Tests erfolgreich sind oder eine
#  maximale Anzahl von Versuchen erreicht ist.
#
#  Verwendung: ./test_and_repair.sh
#
# ==============================================================================

# --- Konfiguration ---
MAX_ATTEMPTS=5
PROJECT_SRC="." # Verzeichnis mit dem Quellcode und den Tests

# --- Hilfsfunktionen für farbige Ausgaben ---
log_info() { echo -e "\033[1;34m[INFO]\033[0m $1"; }
log_success() { echo -e "\033[1;32m[SUCCESS]\033[0m $1"; }
log_warning() { echo -e "\033[1;33m[WARNING]\033[0m $1"; }
log_error() { echo -e "\033[1;31m[ERROR]\033[0m $1"; }
log_step() { echo -e "\n\033[1;36m--- $1 ---\033[0m"; }

# ==============================================================================
#  SCHRITT 1: Sicherheitsüberprüfung (Prüfung des Git-Status)
# ==============================================================================
log_step "SCHRITT 1: Sicherheitsüberprüfung des Git-Repositorys"

if ! git diff --quiet || ! git diff --cached --quiet; then
    log_error "Ihr Arbeitsverzeichnis ist nicht sauber. Bitte committen oder stashen Sie Ihre Änderungen."
    log_error "Dieses Skript wird beendet, um Datenverlust zu verhindern."
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

    # --- Testphase: Führe alle Tests aus und erstelle Berichte ---
    log_info "Führe Tests aus und ermittle die Testabdeckung..."
    # Wir leiten stderr in eine Datei um, um es später zu analysieren
    pytest --cov=$PROJECT_SRC > pytest_results.log 2> pytest_errors.log
    TEST_EXIT_CODE=$?

    # --- Analysephase: Werte die Ergebnisse aus ---
    COMPLETED_TESTS=$(grep -oP '(\d+ passed|\d+ failed)' pytest_results.log | sed 's/ passed//;s/ failed//' | awk '{s+=$1} END {print s}')
    FAILED_TESTS=$(grep -oP '\d+ failed' pytest_results.log | sed 's/ failed//' | awk '{s+=$1} END {print s+0}')
    COVERAGE=$(grep "TOTAL" pytest_results.log | awk '{print $NF}')

    log_info "Testergebnis-Zusammenfassung:"
    echo "  - Abgeschlossene Tests: $COMPLETED_TESTS"
    echo "  - Fehlgeschlagene Tests: $FAILED_TESTS"
    echo "  - Testabdeckung: $COVERAGE"


    if [ $TEST_EXIT_CODE -eq 0 ]; then
        log_success "Alle Tests wurden erfolgreich bestanden!"
        log_step "FINALE BERICHTE"
        cat pytest_results.log
        log_success "Prozess erfolgreich abgeschlossen."
        rm pytest_results.log pytest_errors.log
        exit 0
    else
        log_warning "Fehler in den Tests entdeckt. Starte Reparaturversuch..."
        log_info "Fehlerausgabe der Tests:"
        cat pytest_errors.log
    fi

    # --- Reparaturphase ---

    # Phase 1: Statische Code-Analyse und automatische Korrekturen
    log_info "Reparaturphase 1: Führe automatische Formatierer und Linter aus..."
    black $PROJECT_SRC
    ruff --fix $PROJECT_SRC

    # Phase 2: KI-gestützte Reparatur (konzeptionell)
    # In einem realen Szenario würde hier eine API zu einem LLM aufgerufen werden.
    # Wir simulieren dies, indem wir prüfen, ob die statischen Tools etwas geändert haben.
    # Wenn nicht, würden wir die KI fragen.
    if git diff --quiet; then
        log_warning "Statische Tools konnten keine weiteren Fehler beheben."
        log_info "Reparaturphase 2: KI-gestützte Analyse (Simulation)..."
        log_info "Sende Fehlerprotokoll (pytest_errors.log) an eine KI zur Analyse..."
        # HIER WÜRDE DER API-AUFRUF STEHEN:
        # ai_fix=$(call_ai_api --error_log pytest_errors.log)
        # if [ -n "$ai_fix" ]; then
        #    apply_patch($ai_fix)
        # fi
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