"""Autenticación sin red ni claves reales de Google Cloud."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import ee
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import getter
from errores import ErrorConfiguracion


class CredencialesEarthEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Clave efímera creada solo para probar el parser real, nunca se guarda.
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.cuenta = {
            "type": "service_account", "project_id": "proyecto-prueba",
            "private_key_id": "id-ficticio",
            "private_key": key.private_bytes(serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode(),
            "client_email": "prueba@proyecto-prueba.iam.gserviceaccount.com",
            "token_uri": "https://oauth2.googleapis.com/token",
        }

    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.cache = patch.object(getter, "_EE", None)
        self.cache.start()
        self.addCleanup(self.cache.stop)

    def configure(self, **changes):
        os.environ["GEE_SERVICE_ACCOUNT_JSON"] = json.dumps(dict(self.cuenta, **changes))

    def test_json_real_parser_project_and_cache(self):
        self.configure()
        with patch.object(ee, "Initialize") as initialize, patch.object(ee.data, "setDeadline") as deadline:
            self.assertIs(getter.inicializar_ee(), ee)
            self.assertIs(getter.inicializar_ee(), ee)
        initialize.assert_called_once()
        args = initialize.call_args.kwargs
        self.assertEqual(args["project"], "proyecto-prueba")
        self.assertEqual(args["credentials"].service_account_email, self.cuenta["client_email"])
        deadline.assert_called_once_with(120_000)

    def test_project_override(self):
        self.configure()
        os.environ["GEE_PROJECT_ID"] = "otro-proyecto"
        with patch.object(ee, "Initialize") as initialize, patch.object(ee.data, "setDeadline"):
            getter.inicializar_ee()
        self.assertEqual(initialize.call_args.kwargs["project"], "otro-proyecto")

    def test_local_file_and_json_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "key.json"
            path.write_text(json.dumps(self.cuenta), encoding="utf-8-sig")
            os.environ["GEE_SERVICE_ACCOUNT_FILE"] = str(path)
            self.assertEqual(getter.cargar_cuenta_servicio(), self.cuenta)
            self.configure(project_id="desde-variable")
            path.unlink()
            self.assertEqual(getter.cargar_cuenta_servicio()["project_id"], "desde-variable")

    def test_local_auth_compatibility(self):
        os.environ["GEE_PROJECT_ID"] = "mi-proyecto-local"
        with patch.object(ee, "Initialize") as initialize, patch.object(ee.data, "setDeadline"):
            getter.inicializar_ee()
        initialize.assert_called_once_with(project="mi-proyecto-local")

    def test_invalid_json_never_falls_back(self):
        for invalid in ("", "SECRETO-no-json", "[]", "null", '"doble-codificado"', '{"type":"authorized_user"}'):
            with self.subTest(invalid=invalid), patch.object(ee, "Initialize") as initialize:
                os.environ["GEE_SERVICE_ACCOUNT_JSON"] = invalid
                with self.assertRaises(ErrorConfiguracion) as error:
                    getter.inicializar_ee()
                self.assertNotIn("SECRETO", str(error.exception))
                initialize.assert_not_called()

    def test_each_required_field(self):
        for field in ("project_id", "private_key_id", "private_key", "client_email", "token_uri"):
            with self.subTest(field=field):
                self.configure(**{field: None})
                with self.assertRaisesRegex(ErrorConfiguracion, field):
                    getter.cargar_cuenta_servicio()

    def test_token_endpoint_must_be_google(self):
        self.configure(token_uri="https://example.org/token")
        with self.assertRaisesRegex(ErrorConfiguracion, "token_uri"):
            getter.cargar_cuenta_servicio()

    def test_missing_file(self):
        os.environ["GEE_SERVICE_ACCOUNT_FILE"] = "/no-existe-credencial.json"
        with self.assertRaisesRegex(ErrorConfiguracion, "GEE_SERVICE_ACCOUNT_FILE"):
            getter.cargar_cuenta_servicio()

    def test_bad_private_key_and_retry(self):
        self.configure(private_key="SECRETO-clave-invalida")
        with self.assertLogs(getter.LOG, level="WARNING") as logs:
            with self.assertRaises(ErrorConfiguracion) as error:
                getter.inicializar_ee()
        self.assertNotIn("SECRETO", str(error.exception) + str(logs.output))
        self.assertIsNone(error.exception.__cause__)
        self.assertIsNone(getter._EE)
        self.configure()
        with patch.object(ee, "Initialize"), patch.object(ee.data, "setDeadline"):
            self.assertIs(getter.inicializar_ee(), ee)

    def test_remote_error_does_not_disclose_secret(self):
        self.configure()
        with patch.object(ee, "Initialize", side_effect=RuntimeError("SECRETO")):
            with self.assertLogs(getter.LOG, level="WARNING") as logs:
                with self.assertRaises(ErrorConfiguracion) as error:
                    getter.inicializar_ee()
        self.assertNotIn("SECRETO", str(error.exception) + str(logs.output))
        self.assertIsNone(getter._EE)


if __name__ == "__main__":
    unittest.main()
