# Discord Music Bot

## Reason
Since I used Discord a lot and I wanted to play youtube music to my friends while in call, I thought it would be a fun project to learn Python and more about Discord APIs by following a tutorial on creating a discord music bot.

## What I Added
Originally, the youtube video taught me how to make the bot play music, pause, resume, and queue. 
I added:
1. `/queue` command to show the queue of the songs
2. display of the duration per video
3. ability to play links instead

## How I Implemented this
1. The original video already used a deque to store information of the song's url's and title and other metadata. I just created a for loop that accessed all that stored info and displayed it.
2. I was able to study the syntax and code duration as one of the metadata that is downloaded along with the video.
3. I imported an additional library that can check if something looks like a link. With this I created a seperate function that takes in either a search query or link and decides if its a link. If its a link, it'll have yt-dl view it as so and if not, then view it as a search.

## Youtube Link Test
[Link to Video Showcase](https://youtu.be/gtaMZy2mciU)

**Disclaimer: I did this as only a passion project. I do not intend to monetize or distribute or host this bot publically anywhere. I will also not provide instructions on how to use the bot.**

**Credit goes to: [CreepyD](https://www.youtube.com/@CreepyD) and his tutorial.**


