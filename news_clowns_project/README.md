[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/IzgqG4t0)
[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-2e0aaae1b6195c2367325f4f02e2d04e9abb55f0b24a779b69b11b9e10269abc.svg)](https://classroom.github.com/online_ide?assignment_repo_id=20566289&assignment_repo_type=AssignmentRepo)

Note: API keys in .env files that have been pushed have been since rotated.

Project Title:   News Clown 

Problem Statement: 
	There are so many news sources available to the public, yet most of them report on the same events differently, depending on which political party they are most affiliated with. For instance, Truth Social, an app founded by Trump Media and Technology Group, was launched in response to Donald Trump being banned from Facebook and Twitter in 2021. This app is widely regarded as reporting, often from Donald Trump himself, inaccurate or intentionally misleading interpretations of current events, to shift public opinion in favor of conservative viewpoints. Elon Musk’s purchase of Twitter in 2022, after which he renamed the app “X”, and subsequent involvement in the early days of the Trump administration, sparked outrage for many of X’s users. This, in addition to changes in the app’s functionality and what many considered similar misinformation to that of Truth Social, prompted the independence of Bluesky. 
Bluesky was originally a project developed by Twitter to give more users more control over their content. Similar in functionality to X, Bluesky differs in the experience it offers to users. It allows a user to have a custom feed that can be chosen or created by the user. Additionally, the app allows users to moderate the content that they see on their own feed – flagging posts containing AI, particular politicians they may believe to be corrupt, etc. The massive migration of users from X to Bluesky due to disapproval of Elon Musk’s political involvement in the United States is why the app is generally considered to be more “left-leaning”.
	Given not just these news sources, but others that can be found all over the internet (Fox News, MSNBC, etc.), there becomes an interesting difference in reporting. News outlets that are reporting on the same current event, using the same (or similar) sources, may write a completely different story. Newscaster sets out to assess the general sentiment of each of these platforms, given the variability in reporting. Scraping comment data from the aforementioned sources (Blueskey and Truth Social) , as well as including a more neutral source, like Reddit, as a control group, we may be able to get our finger on the pulse of how users are feeling about the content they are viewing. 


Data Sources/Integration Goal: 
Reddit - gives us more neutral commenter ground. 
Bluesky – Scraping this data will give us a sense of a more liberal/left-leaning commenter point of view. 
Truth Social - Scraping from this source will give a more conservative commenter's point of view. 


Setup Instructions: ** This assumes that you have a docker account & docker application on local machine ** 
1. Clone the repository (git clone [project_url])
2. Create GCP Project, initialize a service account with bucket access and corresponding key, along with creating necessary API keys for the various social media platforms (detailed below).
3. Enable Gemini API (Generative Language API) and record key
4. follow .env template and input personal keys/ IDs
5. create docker hub
6. build each Dockerfile image inside script folders, using docker build --platform linux/amd64 -t (docker-user-id)/<image_name>:latest
7. connect to DockerHub using docker login (input login credentials)
8. push images to docker hub using docker push (docker-user-id)/<image_name>:latest
9. create cloud services on GCP Cloud run for streamlit, keyword search, and the Bluesky scraper. Mount .env file information in the volumes section when configuring parameters. Ensure that the size is at least 4 gigabytes, and that specifically the service account key is not exposed under "variables and secrets", mount container path to be /secret_key/<generated_key_name>.json.
10. create cloud jobs on GCP Cloud run for sentiment analysis and the truth social/ reddit APIs. Apply same configurations including the mounted .env info.
11. ON GCP Cloud Run Jobs, apply triggers that occur at the following times: truthsocial/reddit - 11:30am, sentiment analysis - 12:00 pm (30 11 * * *) (0 12 * * *) 
12. Use cloud scheduler on GCP to schedule the key word scraper at 11:00am (0 11 * * *) and the Bluesky at 11:30am (see cron job text mentioned in 11.)
13. Now can access a fully functional web app using the url corresponding in GCP to your Streamlit Cloud service

To set up the API calls, you need to go to each respective site to find the API keys and other necessary authorization for each site.
- Reddit requires a developer account to access the API. Once a developer account is created, an app must also be created to get the proper identification number, secret code, and creation of a user-agent. A username and password to the account must also be provided when calling the API. With the identification number and code, a token needs to be created to use for an API call.
- Truth Social does not have its own API, so we created an account with Scrape Creators, which had a limited API. Once you create an account, you will see an API key.
- Bluesky uses a public API, so it does not require any keys or authorization codes.
