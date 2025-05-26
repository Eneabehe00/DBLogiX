#!/usr/bin/env python3
"""
Generatore di certificati SSL self-signed per DBLogiX
"""

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime
import ipaddress
import os

def generate_ssl_certificates():
    print("🔐 Generazione certificati SSL in corso...")
    
    # Genera chiave privata RSA
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    # Subject del certificato
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "IT"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Italy"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Local"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "DBLogiX Development"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "IT Department"),
        x509.NameAttribute(NameOID.COMMON_NAME, "192.168.1.26"),
    ])
    
    # Lista di Subject Alternative Names (SAN)
    san_list = [
        x509.DNSName("localhost"),
        x509.DNSName("127.0.0.1"),
        x509.DNSName("192.168.1.26"),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        x509.IPAddress(ipaddress.IPv4Address("192.168.1.26")),
        x509.IPAddress(ipaddress.IPv4Address("0.0.0.0")),
    ]
    
    # Costruisce il certificato
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName(san_list),
        critical=False,
    ).add_extension(
        x509.BasicConstraints(ca=False, path_length=None),
        critical=True,
    ).add_extension(
        x509.KeyUsage(
            digital_signature=True,
            key_encipherment=True,
            key_agreement=False,
            key_cert_sign=False,
            crl_sign=False,
            content_commitment=False,
            data_encipherment=False,
            encipher_only=False,
            decipher_only=False
        ),
        critical=True,
    ).sign(private_key, hashes.SHA256())
    
    # Salva la chiave privata
    with open("key.pem", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Salva il certificato
    with open("cert.pem", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    print("✅ Certificati SSL generati con successo!")
    print("   📄 cert.pem - Certificato pubblico")
    print("   🔑 key.pem - Chiave privata")
    
    # Verifica che i file esistano
    if os.path.exists("cert.pem") and os.path.exists("key.pem"):
        cert_size = os.path.getsize("cert.pem")
        key_size = os.path.getsize("key.pem")
        print(f"   📊 Dimensioni: cert.pem ({cert_size} bytes), key.pem ({key_size} bytes)")
        return True
    else:
        print("❌ Errore: I file certificato non sono stati creati!")
        return False

if __name__ == "__main__":
    try:
        success = generate_ssl_certificates()
        if success:
            print("\n🚀 Pronto per avviare il server HTTPS!")
        else:
            print("\n❌ Generazione fallita!")
    except Exception as e:
        print(f"❌ Errore durante la generazione: {e}")
        import traceback
        traceback.print_exc() 