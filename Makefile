.PHONY: test typecheck lint security syntax-check peer-test topology-test topology-test-all topology-test-ci topology-test-all-real testbed-up testbed-down testbed-up-real testbed-sync-real qemu-status-real performance-report performance-report-all-real uninstall uninstall-local

test:
	python3 -m pytest orchestrator-install-v2/tests/ -v --tb=short

topology-test:
	python3 -m pytest orchestrator-install-v2/tests/test_supported_topologies.py -v --tb=short
	python3 -m pytest peer-install-v2/tests/test_supported_topologies.py -v --tb=short
	python3 -m pytest peer-install-v2/tests/test_integration_mixed_nat_topologies.py -v --tb=short

topology-test-all: topology-test
	python3 -m pytest testbed/tests/test_wireguard_integration.py -v --tb=short

topology-test-ci:
	bash -lc 'set -e; status=0; python3 testbed/scripts/launch-testbed.py up || status=$$?; if [ $$status -eq 0 ]; then $(MAKE) topology-test-all || status=$$?; fi; python3 testbed/scripts/launch-testbed.py down || true; exit $$status'

topology-test-all-real:
	@test -n "$(TESTBED_REAL_ORCH_PASS)" || (echo "TESTBED_REAL_ORCH_PASS is required" >&2; exit 1)
	bash -lc 'set -e; status=0; $(MAKE) topology-test || status=$$?; if [ $$status -eq 0 ]; then $(MAKE) testbed-up-real TESTBED_REAL_ORCH_HOST="$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91)" TESTBED_REAL_ORCH_USER="$(if $(TESTBED_REAL_ORCH_USER),$(TESTBED_REAL_ORCH_USER),root)" TESTBED_REAL_ORCH_PASS="$(TESTBED_REAL_ORCH_PASS)" TESTBED_REAL_ORCH_URL="$(if $(TESTBED_REAL_ORCH_URL),$(TESTBED_REAL_ORCH_URL),http://$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91):8000/RPC2)" || status=$$?; fi; if [ $$status -eq 0 ]; then TESTBED_REAL_ORCH_URL="$(if $(TESTBED_REAL_ORCH_URL),$(TESTBED_REAL_ORCH_URL),http://$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91):8000/RPC2)" python3 -m pytest testbed/tests/test_real_orchestrator_integration.py -v --tb=short || status=$$?; fi; $(MAKE) testbed-down || true; exit $$status'

testbed-up:
	python3 testbed/scripts/launch-testbed.py up

testbed-down:
	python3 testbed/scripts/launch-testbed.py down

testbed-up-real:
	@test -n "$(TESTBED_REAL_ORCH_PASS)" || (echo "TESTBED_REAL_ORCH_PASS is required" >&2; exit 1)
	TESTBED_REAL_ORCH_HOST="$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91)" \
	TESTBED_REAL_ORCH_USER="$(if $(TESTBED_REAL_ORCH_USER),$(TESTBED_REAL_ORCH_USER),root)" \
	TESTBED_REAL_ORCH_PASS="$(TESTBED_REAL_ORCH_PASS)" \
	TESTBED_REAL_ORCH_URL="$(if $(TESTBED_REAL_ORCH_URL),$(TESTBED_REAL_ORCH_URL),http://$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91):8000/RPC2)" \
	python3 testbed/scripts/launch-testbed.py up-real

testbed-sync-real:
	@test -n "$(TESTBED_REAL_ORCH_PASS)" || (echo "TESTBED_REAL_ORCH_PASS is required" >&2; exit 1)
	TESTBED_REAL_ORCH_HOST="$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91)" \
	TESTBED_REAL_ORCH_USER="$(if $(TESTBED_REAL_ORCH_USER),$(TESTBED_REAL_ORCH_USER),root)" \
	TESTBED_REAL_ORCH_PASS="$(TESTBED_REAL_ORCH_PASS)" \
	TESTBED_REAL_ORCH_URL="$(if $(TESTBED_REAL_ORCH_URL),$(TESTBED_REAL_ORCH_URL),http://$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91):8000/RPC2)" \
	python3 testbed/scripts/launch-testbed.py sync-real

qemu-status-real:
	@test -n "$(TESTBED_REAL_ORCH_PASS)" || (echo "TESTBED_REAL_ORCH_PASS is required" >&2; exit 1)
	python3 testbed/scripts/launch-testbed.py status
	python3 testbed/scripts/launch-testbed.py ssh orq rc-service wg-auto-register status || true
	python3 testbed/scripts/launch-testbed.py ssh pa rc-service wg-auto-register status || true
	python3 testbed/scripts/launch-testbed.py ssh pb rc-service wg-auto-register status || true
	sshpass -p "$(TESTBED_REAL_ORCH_PASS)" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $(if $(TESTBED_REAL_ORCH_USER),$(TESTBED_REAL_ORCH_USER),root)@$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91) 'source /etc/linkguard/secrets && orch-cli peer-list --admin-token "$$ADMIN_TOKEN" && wg show wg-HUB'

performance-report:
	@test -n "$(LINKGUARD_REMOTE_PASS)$(TESTBED_REAL_ORCH_PASS)" || (echo "LINKGUARD_REMOTE_PASS or TESTBED_REAL_ORCH_PASS is required" >&2; exit 1)
	LINKGUARD_REMOTE_PASS="$(if $(LINKGUARD_REMOTE_PASS),$(LINKGUARD_REMOTE_PASS),$(TESTBED_REAL_ORCH_PASS))" \
	TESTBED_REAL_ORCH_HOST="$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91)" \
	TESTBED_REAL_ORCH_USER="$(if $(TESTBED_REAL_ORCH_USER),$(TESTBED_REAL_ORCH_USER),root)" \
	python3 scripts/generate-performance-report.py

performance-report-all-real:
	@test -n "$(LINKGUARD_REMOTE_PASS)$(TESTBED_REAL_ORCH_PASS)" || (echo "LINKGUARD_REMOTE_PASS or TESTBED_REAL_ORCH_PASS is required" >&2; exit 1)
	LINKGUARD_REMOTE_PASS="$(if $(LINKGUARD_REMOTE_PASS),$(LINKGUARD_REMOTE_PASS),$(TESTBED_REAL_ORCH_PASS))" \
	TESTBED_REAL_ORCH_HOST="$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91)" \
	TESTBED_REAL_ORCH_USER="$(if $(TESTBED_REAL_ORCH_USER),$(TESTBED_REAL_ORCH_USER),root)" \
	TESTBED_REAL_ORCH_PASS="$(if $(TESTBED_REAL_ORCH_PASS),$(TESTBED_REAL_ORCH_PASS),$(LINKGUARD_REMOTE_PASS))" \
	TESTBED_REAL_ORCH_URL="$(if $(TESTBED_REAL_ORCH_URL),$(TESTBED_REAL_ORCH_URL),http://$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91):8000/RPC2)" \
	python3 scripts/generate-performance-report.py --ensure-qemu-real --teardown-qemu

typecheck:
	python3 -m mypy orchestrator-install-v2/orchestrator/ orchestrator-install-v2/hub-agent.py --ignore-missing-imports --allow-untyped-decorators
	python3 -m mypy peer-install-v2/peer_register/ --ignore-missing-imports --allow-untyped-decorators

security:
	python3 -m bandit -r orchestrator-install-v2/orchestrator/ orchestrator-install-v2/hub-agent.py peer-install-v2/peer_register/ -c .bandit

syntax-check:
	python3 -m py_compile orchestrator-install-v2/orchestrator/__init__.py
	python3 -m py_compile orchestrator-install-v2/orchestrator.py
	python3 -m py_compile orchestrator-install-v2/hub-agent.py
	python3 -m py_compile peer-install-v2/wg-auto-register.py
	python3 -m py_compile peer-install-v2/peer_register/__init__.py
	python3 -m py_compile scripts/generate-performance-report.py
	@echo "Syntax OK"

uninstall:
	@echo "═══ LinkGuard — Desinstalación completa ═══"
	@echo ""
	@echo "Esto ELIMINA todos los componentes de LinkGuard:"
	@echo "  - Servicios, iptables, interfaces y archivos LOCALES"
	@echo "  - Servicios, iptables, wg-HUB y archivos en el ORQUESTADOR (101.44.24.91)"
	@echo "  - Servicio, wg0 y archivos en los PEERS (46.250.168.185, 122.8.179.57, 46.250.162.141)"
	@echo ""
	@echo "Uso:"
	@echo "  sudo bash scripts/uninstall-and-cleanup.sh [opciones]"
	@echo ""
	@echo "Opciones:"
	@echo "  -y / --yes        Modo automático (sin confirmación)"
	@echo "  -n / --dry-run    Solo mostrar qué se haría"
	@echo "  --local-only      Solo limpiar el host local"
	@echo "  --remote-only     Solo limpiar hosts remotos"
	@echo ""
	@echo "Variables requeridas:"
	@echo "  LINKGUARD_REMOTE_PASS o TESTBED_REAL_ORCH_PASS (para limpieza remota)"
	@echo "  O exportarlas antes de ejecutar:"
	@echo '    make uninstall LINKGUARD_REMOTE_PASS="tu_password"'
	@echo ""
	@echo "Ejemplo:"
	@echo "  make uninstall LINKGUARD_REMOTE_PASS='Huawei12'"
	@exit 0

uninstall-local:
	sudo bash scripts/uninstall-and-cleanup.sh --local-only

lint: typecheck security

all: syntax-check lint test
