# ========== VARIABLES AND DATA TYPES ==========

# Numeric
num_var <- 42
# int
int_value <- 32L
print(class(num_var))

# Character
char_var <- "Hello, R!"
print(class(char_var))

# Logical
logic_var <- TRUE
print(class(logic_var))

# Vector
vec <- c(1, 2, 3, 4, 5)
print(vec[0])

# List
list_var <- list(name = "John", age = 25, scores = c(90, 85, 88))
print(list_var)

# ========== IF-ELSE STATEMENTS ==========

age <- 20

if (age >= 18) {
    print("You are an adult")
} else {
    print("You are a minor")
}

# ========== LOOPS ==========

# For loop
print("For Loop:")
for (i in 1:5) {
    print(paste("Iteration", i))
}

# While loop
print("While Loop:")
counter <- 1
while (counter <= 3) {
    print(paste("Count:", counter))
    counter <- counter + 1
}

# Basic R Statistics and Visualizations

# Sample data
data <- c(10, 15, 20, 25, 30, 35, 40, 45, 50, 50)

# ========== BASIC STATISTICS ==========

# Mean
mean_val <- mean(data)
print(paste("Mean:", mean_val))

# Median
median_val <- median(data)
print(paste("Median:", median_val))

# Mode (most frequent value)
mode_val <- names(sort(table(data), decreasing = TRUE))[1]
print(paste("Mode:", mode_val))

# Standard Deviation
sd_val <- sd(data)
print(paste("Standard Deviation:", sd_val))

# Summary statistics
summary(data)

# ========== VISUALIZATIONS ==========

# Box Plot
boxplot(data, main = "Box Plot of Data", ylab = "Values")

# Histogram / Bar Graph
barplot(table(data), main = "Bar Chart", xlab = "Values", ylab = "Frequency")

# Frequency Table
freq_table <- table(data)
print(freq_table)

# Pie Chart
pie(table(data), main = "Pie Chart")

# Line Chart
plot(data, type = "l", main = "Line Chart", xlab = "Index", ylab = "Values")

# Scatter Plot
plot(data, main = "Scatter Plot", xlab = "Index", ylab = "Values", pch = 16)

# ========== DATA NORMALIZATION ==========

# Min-Max Normalization (scales data to 0-1 range)
min_max_norm <- (data - min(data)) / (max(data) - min(data))
print("Min-Max Normalized:")
print(min_max_norm)

# Z-Score Normalization (standardization)
z_score_norm <- (data - mean(data)) / sd(data)
print("Z-Score Normalized:")
print(z_score_norm)

# Mean Normalization
mean_norm <- (data - mean(data)) / (max(data) - min(data))
print("Mean Normalized:")
print(mean_norm)

# ========== NEW DATASET AND NORMALIZATION WITH PLOTS ==========

# Create a new dataset
new_data <- c(5, 12, 18, 22, 30, 35, 28, 40, 45, 50, 38, 42)

# Min-Max Normalization
new_min_max <- (new_data - min(new_data)) / (max(new_data) - min(new_data))

# Z-Score Normalization
new_z_score <- (new_data - mean(new_data)) / sd(new_data)

# Mean Normalization
new_mean_norm <- (new_data - mean(new_data)) / (max(new_data) - min(new_data))

# Create a 2x2 plotting layout
par(mfrow = c(2, 2))

# Plot original data
plot(new_data, type = "l", main = "Original Data", xlab = "Index", ylab = "Values", col = "blue", lwd = 2)

# Plot Min-Max normalized data
plot(new_min_max, type = "l", main = "Min-Max Normalized", xlab = "Index", ylab = "Values", col = "green", lwd = 2)

# Plot Z-Score normalized data
plot(new_z_score, type = "l", main = "Z-Score Normalized", xlab = "Index", ylab = "Values", col = "red", lwd = 2)

# Plot Mean normalized data
plot(new_mean_norm, type = "l", main = "Mean Normalized", xlab = "Index", ylab = "Values", col = "purple", lwd = 2)

# Reset plotting layout
par(mfrow = c(1, 1))
# ========== EXAMPLE WITH SKEWED DATA (BETTER VISUALIZATION) ==========

# Create a dataset with extreme values to show normalization differences
skewed_data <- c(1, 2, 2, 3, 3, 3, 4, 5, 5, 100)

# Apply normalizations
skewed_min_max <- (skewed_data - min(skewed_data)) / (max(skewed_data) - min(skewed_data))
skewed_z_score <- (skewed_data - mean(skewed_data)) / sd(skewed_data)
skewed_mean_norm <- (skewed_data - mean(skewed_data)) / (max(skewed_data) - min(skewed_data))

# Create comparison plots
par(mfrow = c(2, 2))

plot(skewed_data, type = "o", main = "Original Skewed Data", xlab = "Index", ylab = "Values", col = "blue", lwd = 2, pch = 16)

plot(skewed_min_max, type = "o", main = "Min-Max Normalized (0-1)", xlab = "Index", ylab = "Values", col = "green", lwd = 2, pch = 16)

plot(skewed_z_score, type = "o", main = "Z-Score Normalized", xlab = "Index", ylab = "Values", col = "red", lwd = 2, pch = 16)

plot(skewed_mean_norm, type = "o", main = "Mean Normalized", xlab = "Index", ylab = "Values", col = "purple", lwd = 2, pch = 16)

par(mfrow = c(1, 1))

print("Notice how the extreme value (100) affects each normalization method differently!")

