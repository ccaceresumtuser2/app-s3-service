import json
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
MARCADOR_BUCKET = "NOMBRE-DE-TU-BUCKET"


def cargar_politica(ruta, bucket):
	with ruta.open(encoding="utf-8") as archivo:
		politica = json.load(archivo)

	if not isinstance(politica, dict):
		raise ValueError("La politica debe ser un objeto JSON.")

	declaraciones = politica.get("Statement", [])
	if isinstance(declaraciones, dict):
		declaraciones = [declaraciones]
	if not isinstance(declaraciones, list):
		raise ValueError("El campo Statement debe ser un objeto o una lista.")

	for declaracion in declaraciones:
		if not isinstance(declaracion, dict):
			raise ValueError("La politica contiene una declaracion invalida.")
		recurso = declaracion.get("Resource")
		if isinstance(recurso, str):
			declaracion["Resource"] = recurso.replace(MARCADOR_BUCKET, bucket)
		elif isinstance(recurso, list):
			declaracion["Resource"] = [
				elemento.replace(MARCADOR_BUCKET, bucket)
				if isinstance(elemento, str)
				else elemento
				for elemento in recurso
			]

	return politica


def seleccionar_archivo_politica():
	carpeta = Path(__file__).resolve().parent
	archivos = sorted(carpeta.glob("*/politica*.json"))
	if not archivos:
		print("No se encontraron archivos JSON de politicas.")
		return None

	print("Politicas disponibles:")
	for indice, ruta in enumerate(archivos, start=1):
		print(f"{indice}. {ruta.name}")

	try:
		seleccion = int(input("Elige una politica: ")) - 1
	except ValueError:
		print("Seleccion invalida.")
		return None

	if seleccion < 0 or seleccion >= len(archivos):
		print("Seleccion invalida.")
		return None
	return archivos[seleccion]


def confirmar(mensaje):
	return input(f"{mensaje} (s/N): ").strip().lower() == "s"


def aplicar_politica(s3, bucket, ruta_politica):
	try:
		politica = cargar_politica(ruta_politica, bucket)
	except (OSError, json.JSONDecodeError, ValueError) as e:
		print(f"No se pudo cargar la politica: {e}")
		return

	print(f"Se aplicara '{ruta_politica.name}' al bucket '{bucket}'.")
	print("Esta accion reemplaza la politica actual del bucket.")
	print("La politica seleccionada puede permitir lectura publica de objetos.")
	if not confirmar("Continuar?"):
		print("Operacion cancelada.")
		return

	try:
		s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps(politica))
		print(f"Politica aplicada al bucket '{bucket}'.")
	except ClientError as e:
		print(f"AWS no permitio aplicar la politica: {e}")


def eliminar_politica_bucket(s3, bucket):
	print(f"Se eliminara la politica del bucket '{bucket}'.")
	if not confirmar("Continuar?"):
		print("Operacion cancelada.")
		return

	try:
		s3.delete_bucket_policy(Bucket=bucket)
		print(f"Politica eliminada del bucket '{bucket}'.")
	except ClientError as e:
		print(f"AWS no permitio eliminar la politica: {e}")


def crear_cliente_s3():
	return boto3.Session(profile_name="default", region_name=REGION).client("s3")


def main():
	print("1. Aplicar politica desde JSON")
	print("2. Eliminar politica del bucket")
	accion = input("Elige una operacion: ").strip()
	if accion not in ("1", "2"):
		print("Operacion invalida.")
		return

	bucket = input("Nombre del bucket existente: ").strip()
	if not bucket:
		print("No se indico un bucket.")
		return

	s3 = crear_cliente_s3()
	if accion == "1":
		ruta_politica = seleccionar_archivo_politica()
		if ruta_politica is not None:
			aplicar_politica(s3, bucket, ruta_politica)
	elif accion == "2":
		eliminar_politica_bucket(s3, bucket)


if __name__ == "__main__":
	main()
