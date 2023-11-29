# wordcloud-azure-function

An Azure Function that displays a
[word cloud](https://github.com/amueller/word_cloud).

Run locally on Ubuntu 20 WSL.

It's deployed here:  
[`https://wordcloud-azure-function.azurewebsites.net/api/WordCloud?words=hello world`](https://wordcloud-azure-function.azurewebsites.net/api/WordCloud?words=hello%20world)

It can be called with `GET` or `POST`.  
Parameters:
name | default | description
-|-|-
words | *required* | the words to use for the word cloud
height | 4 | height in inches
width | 4 | width in inches
dpi | 100 | resolution: dots (pixels) per inch
color | lightblue | background color
colormap | winter | [Matplotlib colormap](https://matplotlib.org/stable/tutorials/colors/colormaps.html)
