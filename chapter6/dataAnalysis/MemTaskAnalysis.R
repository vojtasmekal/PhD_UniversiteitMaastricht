library(xlsx)

memData <- read.xlsx("D:\\ZeynepStudy\\DATA\\p05\\p05_memResults.xlsx",1)

# Overall accuracy for participant:
mean(memData$correct)

# Accuracy per painting type:
aggregate(memData$correct, by=list(memData$paintingCat), FUN='mean')

# Confidence for incorrect (0) and correct trials(1):
aggregate(memDatat$confidence, by=list(memData$correct), FUN='mean')

# Accuracy per artist:
aggregate(memData$correct, by=list(memData$artist), FUN='mean')

# Select data to include only paintings seen during the VR:
expPaintings <- subset(memData, paintingOld == 1)

# Accuracy per sound type:
aggregate(expPPaintings$correct, by=list(expPaintings$soundType), FUN='mean')

# Accuracy per experimental category
aggregate(expPaintings$correct, by=list(expPaintings$expCond), FUN='mean')
