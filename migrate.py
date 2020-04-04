#! /usr/bin/python
import argparse
import openerplib
#import odoorpc
from copy import copy

description = """This script will connect to the source server and for each product will look for a 
corresponding product in the target server, download the image, and upload it to the target server."""

# define arguments
parser = argparse.ArgumentParser(description)

parser.add_argument('--source-database', type=str, help='[SOURCE] Name of database to connect to')
parser.add_argument('--source-hostname', type=str, help='[SOURCE] Hostname of the OpenERP server', default='localhost')
parser.add_argument('--source-port', type=int, help='[SOURCE] RPC port of the OpenERP server', default=0)
parser.add_argument('--source-protocol', type=str, help='[SOURCE] The protocol used by the RPC connection', default='xmlrpc')
parser.add_argument('--source-username', type=str, help='[SOURCE] Username to connect to the OpenERP server', default='admin')
parser.add_argument('--source-password', type=str, help='[SOURCE] Password to connect to the OpenERP server', default='admin')
parser.add_argument('--source-saas', type=bool, help="[SOURCE] If connecting to SaaS, automatically set appropriate port and protocol", default=False)
parser.add_argument('--source-product-model', type=str, help='[SOURCE] The product model - usually product.product or product.template', default="product.product")

parser.add_argument('--target-database', type=str, help='[TARGET Name of database to connect to')
parser.add_argument('--target-hostname', type=str, help='[TARGET] Hostname of the OpenERP server', default='localhost')
parser.add_argument('--target-port', type=int, help='[TARGET] RPC port of the OpenERP server', default=0)
parser.add_argument('--target-protocol', type=str, help='[TARGET] The protocol used by the RPC connection', default='xmlrpc')
parser.add_argument('--target-username', type=str, help='[TARGET] Username to connect to the OpenERP server', default='admin')
parser.add_argument('--target-password', type=str, help='[TARGET] Password to connect to the OpenERP server', default='admin')
parser.add_argument('--target-saas', type=bool, help="[TARGET] If connecting to SaaS, automatically set appropriate port and protocol", default=False)
parser.add_argument('--target-product-model', type=str, help='[TARGET] The product model - usually product.product or product.template', default="product.product")

# parse arguments
args = parser.parse_args()

# handle saas option
if args.source_saas:
        args.source_protocol = 'xmlrpcs'
        args.source_port = 443

if args.target_saas:
        args.target_protocol = 'xmlrpcs'
        args.target_port = 443

# open connections to each
source_conn = openerplib.get_connection(hostname=args.source_hostname, database=args.source_database, login=args.source_username, password=args.source_password, port=args.source_port or 'auto', protocol=args.source_protocol)
try:
	source_conn.check_login()
except Exception as e:
	print "Could not connect to source server"
	raise

target_conn = openerplib.get_connection(hostname=args.target_hostname, database=args.target_database, login=args.target_username, password=args.target_password, port=args.target_port or 'auto', protocol=args.target_protocol)
try:
	target_conn.check_login()
except Exception as e:
	print "Could not connect to target server"
	raise

# get products from source
source_product_obj = source_conn.get_model(args.source_product_model)
source_imd_obj = source_conn.get_model('ir.model.data')

source_public_categ = source_conn.get_model('product.public.category')
target_public_categ = target_conn.get_model('product.public.category')
source_parent_public_categ_ids = source_public_categ.search([('parent_id', '=', False)])
source_parent_public_categ_recs =  source_public_categ.read(source_parent_public_categ_ids, ['id', 'name', 'sequence'])
source_target_parent_id_map = {}

for source_parent_cat_rec in source_parent_public_categ_recs:
    try:
        pub_cat_found = target_public_categ.search([('name', '=', source_parent_cat_rec['name']), ('sequence', '=', source_parent_cat_rec['sequence']), ('parent_id', '=', False)], limit=1)
        if not pub_cat_found:
            target_categ_id = target_public_categ.create({'name': source_parent_cat_rec['name'], 'sequence': source_parent_cat_rec['sequence']})
            source_target_parent_id_map[str(source_parent_cat_rec['id'])] = target_categ_id
        else:
            source_target_parent_id_map[str(source_parent_cat_rec['id'])] = pub_cat_found[0]
    except Exception as e:
        print e
        print 'ERROR while processing Ecom-Category ' ,  source_parent_cat_rec['id'], ' -- ', source_parent_cat_rec['name']
        
source_child_public_categ_ids = source_public_categ.search([('parent_id', '!=', False)])
source_child_public_categ_recs =  source_public_categ.read(source_child_public_categ_ids, ['id', 'name', 'sequence', 'parent_id'])

for source_cat_rec in source_child_public_categ_recs:
    try:
        if str(source_cat_rec['parent_id']) in source_target_parent_id_map:
            pub_cat_found = target_public_categ.search([('name', '=', source_cat_rec['name']), ('sequence', '=', source_cat_rec['sequence']), ('parent_id', '=', source_target_parent_id_map[source_cat_rec['parent_id']])], limit=1)
            if not pub_cat_found:
                target_categ_id = target_public_categ.create({'name': source_cat_rec['name'], 'sequence': source_cat_rec['sequence'], 'parent_id': source_target_parent_id_map[str(source_cat_rec['parent_id'])]})
                source_target_parent_id_map[str(source_cat_rec['id'])] = target_categ_id
            else:
                source_target_parent_id_map[str(source_cat_rec['id'])] = pub_cat_found[0]
    except Exception as e:
        print e
        print 'ERROR while processing Ecom-Category ' ,  source_cat_rec ['id'], ' -- ', source_cat_rec['name']
#print 'Searching for source products'
#source_product_ids = source_product_obj.search([])
# source_product_imd_ids = source_imd_obj.search([('model', '=', args.source_product_model), ('res_id', 'in', source_product_ids)])
# source_product_imds = source_imd_obj.read(source_product_imd_ids, ['name', 'module', 'res_id'])

# get products from target
target_product_obj = target_conn.get_model(args.target_product_model)
target_imd_obj = target_conn.get_model('ir.model.data')

# source_ecom_categ_obj = source_conn.get_model('product.public.category')
# source_ecom_categ_parent_ids = source_ecom_categ_obj.search([('parent_id', '=', False)])
#if source_ecom_categ_parent_ids:
    
print 'searching for products on target'
target_product_ids = target_product_obj.search([])
target_product_recs = target_product_obj.read(target_product_ids, ['name', 'barcode']) #, default_code, 'image', 'public_categ_ids'

#source_product_ids = source_product_obj.search([])
#source_product_recs = source_product_obj.read(source_product_ids, ['name', 'barcode']) #, default_code, 'public_categ_ids'

common_products = {}
for product in target_product_recs:
    try:
        source_product_found = source_product_obj.search([('barcode', '=', product['barcode'])], limit=1)
        updated = False
        if source_product_found:
        #for source_product in source_product_recs:
            source_product = source_product_obj.read(source_product_found, ['barcode', 'image', 'image_medium', 'public_categ_ids'])[0] #,
            pub_cat_ids = []
            if source_product['public_categ_ids']:
                for categ_id in source_product['public_categ_ids']:
                    if str(categ_id) in source_target_parent_id_map:
                        pub_cat_ids.append(source_target_parent_id_map[str(categ_id)])
            if product['barcode'] == source_product['barcode']:
                #product_image = source_product_obj.read(source_product['id'], ['image']) #, 
                #if product_image[0]['image']:
                if source_product['image']:
                    print 'DONE ', product['id'], ' -- ', product['name']
                    product_vals = {'image': source_product['image'], 'image_medium': source_product['image_medium']}
                    if pub_cat_ids:
                        product_vals['public_categ_ids'] = [(6, 0, pub_cat_ids)]
                    target_product_obj.write(product['id'], product_vals)
                    updated = True
                #common_products[product['id']] = {'image': source_product['image']}
        if not updated:
            print 'SKIPPED ',  product['id'], ' -- ', product['name']
    except Exception:
        print 'ERROR while process ' ,  product['id'], ' -- ', product['name']
        


# for key, val in common_products.items():
#     print 'Updating image for product ' + str(key)
#     target_product_obj.write(key, val)



#args.source_hostname, 
#database=args.source_database, 
#login=args.source_username, 
#password=args.source_password, 
#port=args.source_port or 'auto', 
#protocol=args.source_protocol


# source_odoo = odoorpc.ODOO(args.source_hostname, port=args.source_port or 8069)
# target_odoo = odoorpc.ODOO(args.target_hostname, port=args.target_port or 8069)
# 
# # Check available databases
# #print(odoo.db.list())
# 
# # Login
# source_odoo.login(args.source_database, args.source_username, args.source_password)
# target_odoo.login(args.target_database, args.target_username, args.target_password)
# 
# # Current user
# source_user = source_odoo.env.user
# target_user = target_odoo.env.user
# # print(user.name)            # name of the user connected
# # print(user.company_id.name) # the name of its company
# 
# # Simple 'raw' query
# user_data = odoo.execute('res.users', 'read', [user.id])
# print(user_data)
# 
# # Use all methods of a model
# if args.source_product_model in source_odoo.env and args.source_product_model in target_odoo.env:
#     source_obj = source_odoo.env[args.source_product_model]
#     target_obj = target_odoo.env[args.source_product_model]
#     source_obj_ids = source_obj.search([])
#     target_obj_ids = target_obj.search([])
#     source_objects = source_obj.browse(source_obj_ids)
#     target_objects = target_obj.browse(target_obj_ids)
#     
#     for record in source_objects:
#         print record.name
#         products = [line.product_id.name for line in order.order_line]
#         print products

# Update data through a record
#user.name = "Brian Jones"
    

# for target_product in target_product_recs:
#     if target_product['barcode']:
#         print 'Processing product ' + str(target_product['id'])
#         source_product_found = source_product_obj.search([('barcode', '=', target_product['barcode'])], limit=1)
#         if source_product_found:
#             print 'Product found at source ' + str(source_product_found)
#             source_product_rec = source_product_obj.read(source_product_found, ['name', 'barcode', 'default_code', 'image', 'public_categ_ids'])
#             if source_product_rec[0]['image']:
#                 print 'Updating image for product ' + str(target_product['id'])
#                 target_product_obj.write(target_product['id'], {'image': source_product_rec[0]['image']})
#             else:
#                 print 'Source does not have an image ' 
#         else:
#             print 'NOT Found at SOURCE!!'
#             
#     else:
#         print 'SKIP product ' + str(target_product)
#     print '\n'
        

# target_product_imd_ids = target_imd_obj.search([('model', '=', args.target_product_model), ('res_id', 'in', target_product_ids)])
# target_product_imds = target_product_obj.read(target_product_imd_ids, ['name', 'module', 'res_id'])
# target_product_imd_names = [imd['name'] for imd in target_product_imds]
# 
# # get products common to both instances
# common_product_imds = []
# for source_product_imd in copy(source_product_imds):
# 	for target_product_imd in target_product_imds:
# 		if source_product_imd['name'] == target_product_imd['name']:
# 			common_product_imds.append({'name': source_product_imd['name'], 'source': source_product_imd, 'target': target_product_imd})
# 
# common_product_imds = []
# for source_product_imd in copy(source_product_imds):
#     for target_product_imd in target_product_imds:
#         if source_product_imd['name'] == target_product_imd['name']:
#             common_product_imds.append({'name': source_product_imd['name'], 'source': source_product_imd, 'target': target_product_imd})
# 
# # for each common product, download the image and upload it to the target
# for common_product_imd in common_product_imds:
# 	image = source_product_obj.read(common_product_imd['source']['res_id'], ['image_medium'])['image_medium']
# 	target_product_obj.write(common_product_imd['target']['res_id'], {'image_medium': image})
# 	print 'Done product %d' % common_product_imd['target']['res_id']

print "Finished :)"
