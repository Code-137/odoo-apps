# Payment PagHiper
## Installation
* [Install](https://www.odoo.com/documentation/14.0/applications/general/apps_modules.html) this module in a usual way
## Configuration
* Create a new [PagHiper account](https://dev.paghiper.com/reference/pr%C3%A9-requisitos-e-neg%C3%B3cio) to get your credentials

Go to Account > Configuration > Payment Methods, then:

* Activate the PagHiper payment acquirer and put the API key and the Api Token.
* Create a new journal to this payment method and check the option **receive through PagHiper**

## Usage
### e-commerce
After activation, the payment method will appear as an option to pay at checkout. 

### Common Sale
Select the PagHiper journal in the invoice, then after confirmation, the bank slip will be generated.
