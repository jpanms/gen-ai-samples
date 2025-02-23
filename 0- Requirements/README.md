For this workshop you MUST have the following:

# Requirements
- Visual Studio Code
- Python (tested with 3.10, 3.12)
- Pyhton virtual environment tool (venv)
- An Azure account 
- Azure subscription onboarded into Azure OpenAI
- Necessary permissions to deploy resources in the subscription

# Preparation

## Create the necessary Azure resources
- Insert your subscription ID in the file [createAll.ps1](./scripts/createAll.ps1) and save it. 
    ```
    $SubscriptionId = "<your subscription here>"
    ```
- Modify the password of the admin user of the SQL database the file [deployAll.bicep](./scripts/deployAll.bicep) and save it. 
    ```
    param adminPassword string = 'ChangeYourAdminPassword1'
    ```
- This powershell script will create:
    - A resource group with name starting with 'jpan-genai-workshop'
    - An Azure SQL server with an AdventureWorks sample database
    - An AI Search service
    - An AI Speech service
    - An AI Vision service
    - An Azure OpenAI service with the following models:
        - GPT-4
        - GPT-4o
        - GPT-4o-mini
        - DALL-E
        - Text Embedding Ada


- Go to the azure portal and login with a user that has permissions to create resource groups and resources in your subscription.
- Open the cloud shell in the azure portal as follows:
![Cloud shell](./images/step2.png)

- Upload the files located in the `scripts` folder `createAll.ps1` and `deployAll.bicep`, ONE BY ONE by using the upload file button in the cloud shell:
![Upload](./images/step3.png)

- Run `./createAll.ps1` in the cloud shell to create the resources:
![Upload](./images/step4.png)

    *NOTE: This takes time so be patient.*

- You should get a resource group with the following resources:
![Upload](./images/step5.png)

