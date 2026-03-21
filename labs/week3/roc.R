if(!require(pROC)) install.packages("pROC")
library(pROC)
set.seed(123)
actual_labels <- c(rep(1, 40), rep(0, 60))

# Simulating predicted probabilities (higher for actual positives)
predicted_probs <- c(rnorm(40, mean = 0.7, sd = 0.2), 
                      rnorm(60, mean = 0.3, sd = 0.2))

# Ensure probabilities stay between 0 and 1
predicted_probs <- pmin(pmax(predicted_probs, 0), 1)

# 2. Create the ROC object
roc_curve <- roc(actual_labels, predicted_probs)
auc_value <- auc(roc_curve)


plot(roc_curve, 
     main = paste("ROC Curve for Medical Test (AUC =", round(auc_value, 3), ")"),
     col = "#2c3e50", 
     lwd = 3, 
     identity.col = "red", # Diagonal line (Random Guessing)
     identity.lty = 2,
     print.auc = TRUE,
     auc.polygon = TRUE, 
     auc.polygon.col = "#ecf0f1")

# Add grid for better readability
grid()