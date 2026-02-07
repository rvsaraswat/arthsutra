import React, { useState } from 'react';
import { 
  Grid, 
  Card, 
  CardContent, 
  CardHeader, 
  Typography, 
  Box, 
  TextField, 
  Button, 
  FormControl, 
  InputLabel, 
  Select, 
  MenuItem, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Paper,
  Chip
} from '@mui/material';

// Mock data for trading
const orderHistory = [
  { id: 1, symbol: 'RELIANCE', type: 'Buy', quantity: 10, price: 2450.50, status: 'Completed', date: '2023-06-01' },
  { id: 2, symbol: 'TCS', type: 'Sell', quantity: 5, price: 3200.25, status: 'Completed', date: '2023-06-02' },
  { id: 3, symbol: 'HDFCBANK', type: 'Buy', quantity: 15, price: 1520.75, status: 'Pending', date: '2023-06-03' },
];

const tradingPairs = [
  { symbol: 'RELIANCE', name: 'Reliance Industries', price: 2450.50 },
  { symbol: 'TCS', name: 'Tata Consultancy Services', price: 3200.25 },
  { symbol: 'HDFCBANK', name: 'HDFC Bank', price: 1520.75 },
  { symbol: 'INFY', name: 'Infosys', price: 1350.00 },
];

const Trading = () => {
  const [orderType, setOrderType] = useState('Buy');
  const [selectedStock, setSelectedStock] = useState('');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [stopLoss, setStopLoss] = useState('');
  const [takeProfit, setTakeProfit] = useState('');
  const [orderStatus, setOrderStatus] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    // Mock order submission
    setOrderStatus(`Order placed: ${orderType} ${quantity} shares of ${selectedStock}`);
    // Reset form
    setQuantity('');
    setPrice('');
    setStopLoss('');
    setTakeProfit('');
  };

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Trading
      </Typography>
      
      <Grid container spacing={3}>
        {/* Order Form */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Place Order" />
            <CardContent>
              <form onSubmit={handleSubmit}>
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <FormControl fullWidth>
                      <InputLabel>Order Type</InputLabel>
                      <Select
                        value={orderType}
                        label="Order Type"
                        onChange={(e) => setOrderType(e.target.value)}
                      >
                        <MenuItem value="Buy">Buy</MenuItem>
                        <MenuItem value="Sell">Sell</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  
                  <Grid item xs={12}>
                    <FormControl fullWidth>
                      <InputLabel>Stock</InputLabel>
                      <Select
                        value={selectedStock}
                        label="Stock"
                        onChange={(e) => setSelectedStock(e.target.value)}
                      >
                        {tradingPairs.map((pair) => (
                          <MenuItem key={pair.symbol} value={pair.symbol}>
                            {pair.symbol} - {pair.name} (₹{pair.price})
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                  
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Quantity"
                      type="number"
                      value={quantity}
                      onChange={(e) => setQuantity(e.target.value)}
                      required
                    />
                  </Grid>
                  
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Price (Optional)"
                      type="number"
                      value={price}
                      onChange={(e) => setPrice(e.target.value)}
                    />
                  </Grid>
                  
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Stop Loss (Optional)"
                      type="number"
                      value={stopLoss}
                      onChange={(e) => setStopLoss(e.target.value)}
                    />
                  </Grid>
                  
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Take Profit (Optional)"
                      type="number"
                      value={takeProfit}
                      onChange={(e) => setTakeProfit(e.target.value)}
                    />
                  </Grid>
                  
                  <Grid item xs={12}>
                    <Button 
                      variant="contained" 
                      color="primary" 
                      fullWidth
                      type="submit"
                    >
                      Place Order
                    </Button>
                  </Grid>
                  
                  {orderStatus && (
                    <Grid item xs={12}>
                      <Typography variant="body1" color="primary">
                        {orderStatus}
                      </Typography>
                    </Grid>
                  )}
                </Grid>
              </form>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Order History */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Order History" />
            <CardContent>
              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Stock</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell>Quantity</TableCell>
                      <TableCell>Price</TableCell>
                      <TableCell>Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {orderHistory.map((order) => (
                      <TableRow key={order.id}>
                        <TableCell>{order.symbol}</TableCell>
                        <TableCell>{order.type}</TableCell>
                        <TableCell>{order.quantity}</TableCell>
                        <TableCell>₹{order.price}</TableCell>
                        <TableCell>
                          <Chip 
                            label={order.status} 
                            color={order.status === 'Completed' ? 'success' : 'warning'} 
                            variant="outlined" 
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Trading Signals */}
        <Grid item xs={12}>
          <Card>
            <CardHeader title="Trading Signals" />
            <CardContent>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" component="h3" gutterBottom>
                        Buy Signal
                      </Typography>
                      <Typography variant="body1">
                        RELIANCE - Strong fundamental analysis
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Confidence: 92%
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" component="h3" gutterBottom>
                        Sell Signal
                      </Typography>
                      <Typography variant="body1">
                        TCS - Technical resistance
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Confidence: 85%
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" component="h3" gutterBottom>
                        Watchlist
                      </Typography>
                      <Typography variant="body1">
                        HDFCBANK - Positive sentiment
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Confidence: 78%
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6" component="h3" gutterBottom>
                        Alert
                      </Typography>
                      <Typography variant="body1">
                        INFY - Price approaching resistance
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Confidence: 65%
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Trading;