import React from 'react';
import { 
  Grid, 
  Card, 
  CardContent, 
  CardHeader, 
  Typography, 
  Box, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Paper,
  Chip
} from '@mui/material';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

// Mock data for portfolio
const portfolioData = [
  { symbol: 'RELIANCE', name: 'Reliance Industries', quantity: 10, avgPrice: 2400.50, currentPrice: 2450.50, change: 2.08 },
  { symbol: 'TCS', name: 'Tata Consultancy Services', quantity: 5, avgPrice: 3150.25, currentPrice: 3200.25, change: 1.59 },
  { symbol: 'HDFCBANK', name: 'HDFC Bank', quantity: 15, avgPrice: 1480.75, currentPrice: 1520.75, change: 2.70 },
  { symbol: 'INFY', name: 'Infosys', quantity: 20, avgPrice: 1300.00, currentPrice: 1350.00, change: 3.85 },
];

const allocationData = [
  { name: 'RELIANCE', value: 35 },
  { name: 'TCS', value: 25 },
  { name: 'HDFCBANK', value: 20 },
  { name: 'INFY', value: 20 },
];

const performanceData = [
  { month: 'Jan', profit: 10000 },
  { month: 'Feb', profit: 15000 },
  { month: 'Mar', profit: 8000 },
  { month: 'Apr', profit: 12000 },
  { month: 'May', profit: 20000 },
  { month: 'Jun', profit: 25000 },
];

const COLORS = ['#1976d2', '#dc004e', '#4caf50', '#ff9800'];

const Portfolio = () => {
  const totalValue = portfolioData.reduce((sum, stock) => sum + (stock.quantity * stock.currentPrice), 0);
  const totalProfit = portfolioData.reduce((sum, stock) => {
    const profit = (stock.currentPrice - stock.avgPrice) * stock.quantity;
    return sum + profit;
  }, 0);

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Portfolio
      </Typography>
      
      <Grid container spacing={3}>
        {/* Portfolio Summary */}
        <Grid item xs={12}>
          <Card>
            <CardHeader title="Portfolio Summary" />
            <CardContent>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Typography variant="h5" component="h2">
                    Total Portfolio Value: ₹{totalValue.toLocaleString()}
                  </Typography>
                  <Typography variant="h6" component="h3">
                    Total Profit/Loss: ₹{totalProfit.toLocaleString()} ({((totalProfit / (totalValue - totalProfit)) * 100).toFixed(2)}%)
                  </Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie
                        data={allocationData}
                        cx="50%"
                        cy="50%"
                        labelLine={true}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      >
                        {allocationData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Portfolio Holdings */}
        <Grid item xs={12}>
          <Card>
            <CardHeader title="Portfolio Holdings" />
            <CardContent>
              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Stock</TableCell>
                      <TableCell>Quantity</TableCell>
                      <TableCell>Avg Price</TableCell>
                      <TableCell>Current Price</TableCell>
                      <TableCell>Change</TableCell>
                      <TableCell>Profit/Loss</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {portfolioData.map((stock) => {
                      const currentValue = stock.quantity * stock.currentPrice;
                      const profitLoss = (stock.currentPrice - stock.avgPrice) * stock.quantity;
                      const profitLossPercent = ((stock.currentPrice - stock.avgPrice) / stock.avgPrice) * 100;
                      
                      return (
                        <TableRow key={stock.symbol}>
                          <TableCell>
                            <Typography variant="h6">{stock.symbol}</Typography>
                            <Typography variant="body2" color="text.secondary">{stock.name}</Typography>
                          </TableCell>
                          <TableCell>{stock.quantity}</TableCell>
                          <TableCell>₹{stock.avgPrice}</TableCell>
                          <TableCell>₹{stock.currentPrice}</TableCell>
                          <TableCell>
                            <Chip 
                              label={`${profitLossPercent.toFixed(2)}%`} 
                              color={profitLossPercent >= 0 ? 'success' : 'error'} 
                              variant="outlined" 
                            />
                          </TableCell>
                          <TableCell>
                            ₹{profitLoss.toLocaleString()}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Performance Chart */}
        <Grid item xs={12}>
          <Card>
            <CardHeader title="Portfolio Performance" />
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={performanceData}
                  margin={{
                    top: 5,
                    right: 30,
                    left: 20,
                    bottom: 5,
                  }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="profit" fill="#1976d2" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Portfolio;