import ConfigParser
import os

config = ConfigParser.ConfigParser()
config.read("input.ini")
password = config.get('ca','keystore_password')
ca_dn = config.get('ca','ca_dn')
host_dn = config.get('server_certs','cn_template')
hostnames =  config.get('server_certs','hostnames').split(",")
format_pkcs12=config.get('cert_format','pkcs12')
format_pkcs7=config.get('cert_format','pkcs7')


def java():
    java_home = os.environ.get("JAVA_HOME", None)
    if java_home:
        keytool_cmd = os.path.join(java_home, "bin", "keytool")
    else:
        keytool_cmd = which("keytool")


'''Function to create RootCA and CA signed JKS keystore'''

def keystore_create_rootca():
    genkey_cmd="keytool -genkeypair -v -alias rootca -dname {0} -keystore rootca.jks -keypass {1} -storepass {1} -keyalg RSA -keysize 4096 -ext KeyUsage:critical=\"keyCertSign\" -ext BasicConstraints:critical=\"ca:true\" -validity 9999".format(ca_dn, password)
    print("====Creating RootCA with DN: %s===="%(ca_dn))
    rootca_cmd_truststore = "keytool -import -v -alias rootca -file rootca.crt -keystore rootca-truststore.jks -storetype JKS -storepass {0} -noprompt".format(password)
    export_ca="keytool -export -v -alias rootca -file rootca.crt -keypass {0} -storepass {0} -keystore rootca.jks -rfc".format(password)
    export_capem="keytool -exportcert -alias rootca -keystore rootca-truststore.jks -rfc -file CARoot.pem -storepass {0}".format(password)
    rename_truststore="cp -p rootca-truststore.jks truststore.jks"

    os.popen(genkey_cmd)
    os.popen(export_ca)
    os.popen(rootca_cmd_truststore)
    os.popen(export_capem)
    os.popen(rename_truststore)


def keystore_create_jks(host):
    host_dn_format=host_dn.format(host)
    print("====Creating keystore for the host : %s====" % (host))
    cmd_cert="keytool -genkeypair -v -alias {0} -dname {2} -keystore {0}.jks -keypass {1} -storepass {1} -keyalg RSA -keysize 2048 -validity 365".format(host,password,host_dn_format)
    cmd_csr="keytool -certreq -v -alias {0} -keypass {1} -storepass {1} -keystore {0}.jks -file {0}.csr".format(host,password)
    cmd_crt="keytool -gencert -v -alias rootca -keypass {1} -storepass {1} -keystore rootca.jks -infile {0}.csr -outfile {0}.crt -ext KeyUsage:critical=\"digitalSignature,keyEncipherment\" -ext EKU=\"serverAuth,clientAuth\" -ext SAN=\"DNS:{0}\" -validity 365 -rfc".format(host,password)
    cmd_keystore_sign="keytool -import -v -alias {0} -file {0}.crt -keystore {0}.jks -storetype JKS -storepass {1}".format(host,password)
    cmd_trust="keytool -import -v -alias rootca -file rootca.crt -keystore {0}.jks -storetype JKS -storepass {1} -noprompt".format(host,password)

    cmd_exportcert="keytool -exportcert -alias {0} -keystore {0}.jks -rfc -file {0}_cert.pem -storepass {1}".format(host,password)
    cmd_importcert="keytool -v -importkeystore -srckeystore {0}.jks -srcalias {0} -destkeystore {0}.p12 -deststoretype PKCS12 -storepass {1} -srcstorepass {1}".format(host,password)
    cmd_exportkey="openssl pkcs12 -in {0}.p12 -nocerts -out {0}_key.pem -password pass:{1} -passin pass:{1} -passout pass:{1}".format(host,password)

    cmd_importcert_into_trust="keytool -import -alias {0} -file {0}_cert.pem -keystore truststore.jks -storepass {1}".format(host,password)

    os.popen(cmd_cert)
    os.popen(cmd_csr)
    os.popen(cmd_crt)
    os.popen(cmd_trust)
    os.popen(cmd_keystore_sign)

    os.popen(cmd_exportcert)
    os.popen(cmd_importcert)
    os.popen(cmd_exportkey)
    print("====Importing {0} into truststore====".format(host))
    os.popen(cmd_importcert_into_trust)

'''Function to convert JKS to PKCS12 fromat'''

def convert_pkcs12(host):
    convert_cmd_pkcs12="keytool -importkeystore -destkeystore {0}.p12 -deststoretype PKCS12  -deststorepass {1} -destkeypass {1} -srcstoretype JKS  -srcalias {0}  -srckeystore {0}.jks -srcstorepass {1} -srckeypass {1}  -noprompt".format(host,password)
    os.popen(convert_cmd_pkcs12)

'''Function to convert PKCS12 to PEM fromat'''

def convert_pem(host):
    convert_cmd_pem="openssl pkcs12 -in {0}.p12 -out {0}.pem -nodes -password pass:{1}".format(host,password)
    convert_cmd_key = "openssl pkcs12 -in {0}.p12 -nocerts -out {0}.key  -password pass:{1} -passout pass:{1}".format(host, password)
    os.popen(convert_cmd_pem)
    os.popen(convert_cmd_key)


'''Function to convert PKCS12 to PEM fromat'''

def convert_pkcs7(host):
    convert_cmd_pkcs7="openssl crl2pkcs7 -nocrl -certfile {0}.pem -out {0}.p7b".format(host)
    os.popen(convert_cmd_pkcs7)


def main():
    keystore_create_rootca()
    for i in range(len(hostnames)):
        host = hostnames[i]
        keystore_create_jks(host)
        if format_pkcs12 == 'True':
            convert_pkcs12(host)

        if format_pkcs7 == 'True':
            print("====Converting to PKCS12 format====")
            convert_pkcs12(host)
            print("===Converting to PEM format===")
            convert_pem(host)
            print("===Converting to PKCS7 format===")
            convert_pkcs7(host)

main()
